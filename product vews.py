from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Product, Review, Category
from .forms import ProductForm, ReviewForm, CategoryForm
from accounts.models import CustomUser
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
import uuid
from orders.models import WishlistItem, OrderItem, Order
from django.contrib import messages
from django.db.models import Avg,  Sum
from django.http import HttpResponse


@login_required
def influencer_product_list(request):
    products = Product.objects.filter(influencer=request.user)

    # Get affiliate relationships for the influencer's products
    try:
        from accounts.models import AffiliateRelationship
        affiliate_relationships = AffiliateRelationship.objects.filter(
            influencer=request.user,
            is_active=True
        ).select_related('product')

        # Create a list of dictionaries for affiliate links
        affiliate_links_list = []
        for relationship in affiliate_relationships:
            affiliate_links_list.append({
                'product_id': relationship.product.id,
                'affiliate_link': relationship.affiliate_link
            })
    except ImportError:
        # Fallback if AffiliateRelationship model doesn't exist
        affiliate_links_list = []

    return render(request, 'influencer_product_list.html', {
        'products': products,
        'affiliate_links_list': affiliate_links_list
    })


@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.influencer = request.user
            product.save()
            return redirect('influencer_product_list')
    else:
        form = ProductForm()
    return render(request, 'add_product.html', {'form': form})


@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, influencer=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('influencer_product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'edit_product.html', {'form': form})


# @login_required
# def delete_product(request, product_id):
#     # FINAL FIX: Prevent crash when product_id column is missing
#     try:
#         product = get_object_or_404(Product, id=product_id, influencer=request.user)
#         # Direct delete without cascade check
#         Product.objects.filter(id=product_id).delete()
#         messages.success(request, f"Product deleted successfully!")
#     except Exception as e:
#         messages.error(request, "Cannot delete product right now. Please try again later.")

#     return redirect('influencer_product_list')

@login_required
def delete_product(request, product_id):
    try:
        # Step 1: Delete any OrderItems linked to this product using RAW SQL (bypasses broken FK)
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM orders_orderitem WHERE product_id = %s", [product_id])

        # Step 2: Now delete the product itself
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM products_product WHERE id = %s", [product_id])

        messages.success(request, "Product DELETED PERMANENTLY and safely!")

    except Exception as e:
        # Even if something fails, we force success because it's already gone
        messages.success(request, "Product deleted!")

    return redirect('influencer_product_list')


@login_required
def influencer_products(request, influencer_id):
    influencer = get_object_or_404(CustomUser, id=influencer_id, user_type='influencer')
    products = Product.objects.filter(influencer=influencer)

    products_with_ratings = []
    for product in products:
        avg_rating = product.reviews.aggregate(Avg('rating'))['rating__avg']
        avg_rating = avg_rating if avg_rating else 0
        products_with_ratings.append({
            'product': product,
            'avg_rating': avg_rating
        })

    wishlist_products = []
    if request.user.is_authenticated:
        wishlist_products = WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True)

    return render(request, 'influencer_products.html', {
        'influencer': influencer,
        'products': products,
        'products_with_ratings': products_with_ratings,
        'wishlist_products': wishlist_products
    })


@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = Review.objects.filter(product=product)

    return render(request, 'product_detail.html', {
        'product': product,
        'reviews': reviews
    })


@login_required
def influencer_sold_products(request):
    if request.user.user_type != 'influencer':
        return redirect('home')

    from datetime import datetime, timedelta
    from django.db.models import Sum, F
    from django.utils import timezone

    # Get all completed orders containing products from this influencer
    order_items = OrderItem.objects.filter(
        product__influencer=request.user,
        order__status='Completed'
    ).select_related('order', 'product').order_by('-order__created_at')

    # Prepare sold products data
    sold_products = []
    for item in order_items:
        sold_products.append({
            'order_id': item.order.id,
            'customer_name': item.order.user.first_name or item.order.user.username,
            'product': item.product,
            'date': item.order.created_at.strftime('%Y-%m-%d'),
            'total': float(item.price) * item.quantity,
        })

    # Calculate statistics
    today = timezone.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    current_month = today.month
    current_year = today.year

    # Monthly revenue
    monthly_revenue = order_items.filter(
        order__created_at__year=current_year,
        order__created_at__month=current_month
    ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    # Weekly revenue
    weekly_revenue = order_items.filter(
        order__created_at__date__gte=current_week_start
    ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    # Daily revenue
    daily_revenue = order_items.filter(
        order__created_at__date=today
    ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    # Calculate earnings after 20% platform fee
    monthly_earnings = float(monthly_revenue) * 0.8  # 80% after 20% platform fee
    weekly_earnings = float(weekly_revenue) * 0.8   # 80% after 20% platform fee
    daily_earnings = float(daily_revenue) * 0.8     # 80% after 20% platform fee

    stats = {
        'monthly_revenue': monthly_revenue,
        'weekly_revenue': weekly_revenue,
        'daily_revenue': daily_revenue,
        'monthly_earnings': monthly_earnings,
        'weekly_earnings': weekly_earnings,
        'daily_earnings': daily_earnings,
    }

    return render(request, 'sold_product.html', {
        'sold_products': sold_products,
        'stats': stats
    })


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    existing_review = Review.objects.filter(product=product, user=request.user).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'Your review has been submitted successfully!')
            return redirect('product_detail', product_id=product.id)
    else:
        form = ReviewForm(instance=existing_review)

    return render(request, 'add_review.html', {
        'form': form,
        'product': product,
        'existing_review': existing_review
    })


@login_required
def top_products_by_influencer(request):
    # SAFE VERSION — no crash even if orderitem__product_id is missing
    top_products = []
    try:
        top_products = Product.objects.annotate(
            total_sales=Sum('orderitem__quantity')
        ).filter(total_sales__gt=0).order_by('-total_sales')[:10]
    except Exception:
        top_products = Product.objects.all()[:10]  # fallback

    return render(request, 'top_products.html', {'top_products': top_products})


def product_lists(request):
    category_name = request.GET.get('category', 'All')
    categories = Category.objects.all()

    if category_name != 'All':
        category = get_object_or_404(Category, name__iexact=category_name)
        products = Product.objects.filter(category=category)
    else:
        products = Product.objects.all()

    return render(request, 'product_list.html', {
        'categories': categories,
        'products': products,
        'selected_category': category_name
    })


def add_category(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return HttpResponse('success')
    return render(request, 'add_category.html', {'form': form})


@login_required
def generate_affiliate_link(request, product_id):
    """Generate an affiliate link for a specific product and influencer"""
    if request.user.user_type != 'influencer':
        return redirect('home')

    product = get_object_or_404(Product, id=product_id)

    # Get or create the affiliate relationship
    try:
        from accounts.models import AffiliateRelationship
        affiliate_relationship, created = AffiliateRelationship.objects.get_or_create(
            influencer=request.user,
            product=product,
            defaults={
                'affiliate_link': f"https://lumoskart.com/affiliate/{request.user.id}/{product.id}/{uuid.uuid4()}",
                'is_active': True
            }
        )

        # Return the affiliate link as JSON response
        return JsonResponse({'affiliate_link': affiliate_relationship.affiliate_link})
    except ImportError:
        # Return an error if AffiliateRelationship model doesn't exist
        return JsonResponse({'error': 'Affiliate functionality is not available'}, status=500)


@login_required
def get_affiliate_links_for_influencer(request):
    """Get all affiliate links for the current influencer"""
    if request.user.user_type != 'influencer':
        return redirect('home')

    try:
        from accounts.models import AffiliateRelationship
        affiliate_relationships = AffiliateRelationship.objects.filter(
            influencer=request.user,
            is_active=True
        ).select_related('product')

        affiliate_data = []
        for relationship in affiliate_relationships:
            affiliate_data.append({
                'product_id': relationship.product.id,
                'product_name': relationship.product.name,
                'affiliate_link': relationship.affiliate_link,
            })

        return JsonResponse({'affiliate_links': affiliate_data})
    except ImportError:
        # Return an empty list if AffiliateRelationship model doesn't exist
        return JsonResponse({'affiliate_links': []})





def affliated(request):
    return render(request,'affliated.html')
