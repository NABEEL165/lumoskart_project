from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from products.models import Product
from .models import CartItem, WishlistItem, Address, Order, OrderItem
from .forms import AddressForm
from django.contrib import messages
from django.http import HttpResponse

import razorpay
from decimal import Decimal
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import transaction





@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('view_cart')


@login_required
def view_cart(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.total_price() for item in cart_items)
    return render(request, 'cart.html', {'cart_items': cart_items, 'total': total})



@login_required
def update_cart_item(request, item_id, action):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)

    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease' and cart_item.quantity > 1:
        cart_item.quantity -= 1

    cart_item.save()
    return redirect('view_cart')


@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    if request.method == 'POST':
        cart_item.delete()
    return redirect('view_cart')


@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    request.session['buy_now_product_id'] = product.id
    request.session['buy_now_quantity'] = 1
    return redirect('checkout')





@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    user = request.user
    print(f"User ID during Wishlist toggle: {user.id}")  # Debug to ensure correct user

    with transaction.atomic():
        wishlist_item, created = WishlistItem.objects.get_or_create(user=user, product=product)

        if not created:
            wishlist_item.delete()
            return JsonResponse({'status': 'removed'})
        else:
            return JsonResponse({'status': 'added'})


@login_required
def wishlist_view(request):
    wishlist_items = WishlistItem.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def select_or_add_address(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('checkout')
    else:
        form = AddressForm()

    addresses = request.user.addresses.all()

    return render(request, 'select_address.html', {'form': form, 'addresses': addresses})


@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    return redirect('select_address')


@login_required
def confirm_order(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user)
    address = Address.objects.filter(user=user).last()

    order = Order.objects.create(user=user, address=address, total_amount=0)
    total = 0

    for item in cart_items:
        product = item.product
        if product.stock >= item.quantity:
            product.stock -= item.quantity
            product.save()
        else:
            return HttpResponse("Not enough stock for {}".format(product.name))

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=item.quantity,
            price=product.price
        )
        total += item.quantity * product.price

    order.total_amount = total
    order.save()
    order.status = Order.COMPLETED
    order.save()
    cart_items.delete()

    return redirect('order_summary', order_id=order.id)


@login_required
def order_summary(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'order_summary.html', {'order': order})


def place_order(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Assume quantity comes from POST data
    quantity = int(request.POST.get('quantity', 1))  # Default to 1 if not provided

    if product.stock >= quantity:
        product.stock -= quantity
        product.save()
        # Continue with order creation logic (save Order model etc.)

        messages.success(request, f'Order placed successfully for {quantity} item(s)!')
        return redirect('order_success_page')  # your success page
    else:
        messages.error(request, 'Sorry, not enough stock available!')
        return redirect('product_list')


from django.db.models import Sum


def report_view(self, request):
    product_sales = (
        OrderItem.objects
        .values('product__name', 'product__influencer__username')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')
    )
    return render(request, 'order_report.html', {
        'title': 'Product Sales Report',
        'product_sales': product_sales,
    })




# helper to convert Decimal/float rupees to integer paise
def rupees_to_paise(amount):
    # ensure Decimal to avoid floating mistakes
    return int( (Decimal(amount)).quantize(Decimal("0.01")) * 100 )

def create_order_from_cart(user, address=None):
    """
    Create Order + OrderItems for the user's cart.
    Returns (order, message) or raises Exception on stock problems.
    """
    cart_items = CartItem.objects.filter(user=user)
    if not cart_items.exists():
        raise ValueError("Cart is empty")

    # Use atomic transaction to keep consistency
    with transaction.atomic():
        # Create order record with total 0 for now
        order = Order.objects.create(user=user, address=address, total_amount=0, status=Order.PENDING)
        total = Decimal('0.00')

        for item in cart_items.select_related('product'):
            product = item.product
            if product.stock < item.quantity:
                raise ValueError(f"Not enough stock for {product.name}")
            # Reduce stock
            product.stock -= item.quantity
            product.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                price=product.price
            )
            total += Decimal(item.quantity) * Decimal(product.price)

        order.total_amount = total
        # keep as Pending until payment verified
        order.save()
        # don't delete cart_items here — we'll clear them after successful payment
        return order

# ---------- Checkout view creates a Razorpay order ----------
@login_required
def checkout(request):
    """
    Shows checkout page with addresses and creates a Razorpay order
    (Razorpay order is created server-side so we can verify server-side later).
    """
    # Check if this is a buy_now request
    is_buy_now = 'buy_now_product_id' in request.session
    
    if is_buy_now:
        # For buy now, create a temporary cart-like object
        product_id = request.session.get('buy_now_product_id')
        quantity = request.session.get('buy_now_quantity', 1)
        
        if product_id:
            product = get_object_or_404(Product, id=product_id)
            # Create a mock cart item for the template
            from django.db import models
            from collections import namedtuple
            
            # Create a mock CartItem-like object for buy now
            class MockCartItem:
                def __init__(self, product, quantity):
                    self.product = product
                    self.quantity = quantity
                    
                @property
                def total_price(self):
                    return self.product.price * self.quantity
            
            mock_item = MockCartItem(product, quantity)
            cart_items = [mock_item]
            total_for_calculation = product.price * quantity
        else:
            messages.info(request, "Product not found for buy now.")
            return redirect('view_cart')
    else:
        cart_items = CartItem.objects.filter(user=request.user)
        if not cart_items.exists():
            messages.info(request, "Your cart is empty.")
            return redirect('view_cart')
        total_for_calculation = sum(Decimal(item.product.price) * item.quantity for item in cart_items)

    # compute total as Decimal
    if is_buy_now:
        subtotal = total_for_calculation
    else:
        subtotal = sum(Decimal(item.product.price) * item.quantity for item in cart_items)
    
    # Calculate GST (18% of subtotal)
    gst_rate = Decimal('0.18')
    gst_amount = subtotal * gst_rate
    
    # Fixed courier charge
    courier_charge = Decimal('100.00')
    
    # Calculate grand total
    grand_total = subtotal + gst_amount + courier_charge
    
    # Convert grand total to paise for Razorpay (since we want to charge the full amount including GST and courier)
    total_paise = rupees_to_paise(grand_total)

    # get addresses for user (to let them choose)
    addresses = request.user.addresses.all()
    address_form = AddressForm()

    # create a Razorpay order (server-side)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    razorpay_order = client.order.create(dict(
        amount=total_paise,
        currency='INR',
        payment_capture='1'  # auto-capture
    ))

    context = {
        'cart_items': cart_items,
        'total': subtotal,
        'gst_amount': gst_amount,
        'courier_charge': courier_charge,
        'grand_total': grand_total,
        'is_buy_now': is_buy_now,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'addresses': addresses,
        'address_form': address_form,
    }
    return render(request, 'checkout.html', context)

# ---------- endpoint to add/select an address via POST (AJAX optional) ----------
@login_required
def add_address_and_return(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return JsonResponse({'status': 'ok', 'address_id': address.id, 'address_text': str(address)})
    return JsonResponse({'status': 'error'}, status=400)

# ---------- Payment handler: verifies signature and finalizes the order ----------
@csrf_exempt
@login_required
def paymenthandler(request):
    """
    Razorpay will post payment details here (our checkout form posts via JS).
    We verify signature, then create Order and OrderItems (or mark existing),
    clear cart, and show order summary.
    """
    if request.method != "POST":
        return HttpResponse("Invalid request method", status=405)

    # read posted params
    payment_id = request.POST.get('razorpay_payment_id', '')
    razorpay_order_id = request.POST.get('razorpay_order_id', '')
    signature = request.POST.get('razorpay_signature', '')
    selected_address_id = request.POST.get('selected_address_id')  # ID from radio/select

    if not (payment_id and razorpay_order_id and signature):
        return HttpResponse("Missing payment parameters", status=400)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }

    try:
        # verify signature
        client.utility.verify_payment_signature(params_dict)
    except Exception as e:
        # signature verification failed
        return HttpResponse("Payment verification failed: " + str(e), status=400)

    # signature ok → create Order from cart and mark completed
    try:
        address = None
        if selected_address_id:
            address = get_object_or_404(Address, id=selected_address_id, user=request.user)

        # create order and items (this will reserve stock)
        order = create_order_from_cart(request.user, address=address)

        # mark order paid/completed
        order.status = Order.COMPLETED
        order.save()

        # clear user's cart
        CartItem.objects.filter(user=request.user).delete()
        
        # clear buy_now session data if it exists
        if 'buy_now_product_id' in request.session:
            del request.session['buy_now_product_id']
        if 'buy_now_quantity' in request.session:
            del request.session['buy_now_quantity']

        # Optionally, store razorpay ids somewhere (extend Order model if you like)
        # e.g., order.razorpay_payment_id = payment_id ; order.save()

        # show the order summary page
        return redirect('order_summary', order_id=order.id)
    except ValueError as ve:
        # stock problem or empty cart
        return HttpResponse(str(ve), status=400)
    except Exception as ex:
        return HttpResponse("Error creating order: " + str(ex), status=500)

# ---------- Order summary ----------
@login_required
def order_summary(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_summary.html', {'order': order})




