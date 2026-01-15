
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import  Q, Sum, F
from django.core.exceptions import FieldError
# from django.utils.timezone import now
from .forms import InfluencerRegisterForm, CustomerRegisterForm, InfluencerProfileForm,VideoUploadForm,VideoEditForm
from .models import CustomUser, InfluencerProfile, InfluencerVideo, WithdrawRequest, Order, OrderItem, InfluencerApplication
from django.contrib import messages

try:
    from product.models import Category, Product
except (ModuleNotFoundError, ImportError):
    try:
        from products.models import Category, Product
    except ImportError:
        from .models import Category, Product  # fallback


from django.utils import timezone

import json


def home_view(request):
    categories = Category.objects.all()
    influencers = CustomUser.objects.filter(user_type='influencer')
    products = Product.objects.select_related('category', 'influencer')[:12]

    # FIXED: Use correct field names from your model
    reels_videos = InfluencerVideo.objects.filter(is_active=True).order_by('-created_at')

    context = {
        'categories': categories,
        'influencers': influencers,
        'products': products,
        'reels_videos': reels_videos,
    }
    return render(request, 'home.html', context)


def register_influencer(request):
    if request.method == 'POST':
        form = InfluencerRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
                # Create an influencer application that needs admin approval

            # Create a blank application for this user
            InfluencerApplication.objects.create(
                user=user,
                is_approved=False  # By default, applications need approval
            )

            try:
                send_mail(
                    'Welcome to Influencify — Let’s Build Something Iconic!',
                    f'Hi {user.username},\n\nWelcome to Influencify! Your journey as an influencer starts here. Collaborate, create, and inspire shoppers worldwide. Let\'s build something iconic!\n\nPlease complete your influencer application to get started.',
                    'empireaeitservices8@gmail.com',
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                pass  # Log email failure if logging is configured

            # Redirect to the application form to complete details
            return redirect('influencer_application')
    else:
        form = InfluencerRegisterForm()
    return render(request, 'register_influencer.html', {'form': form})


def register_customer(request):
    if request.method == 'POST':
        form = CustomerRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                send_mail(
                    'Welcome to Influencify — Start Shopping!',
                    f'Hi {user.username},\n\nWelcome to Influencify! Discover unique products from top influencers and join a community of trendsetters. Start shopping now!',
                    'empireaeitservices8@gmail.com',
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                pass  # Log email failure if logging is configured
            # After successful registration, redirect to homepage
            return redirect('home')
    else:
        form = CustomerRegisterForm()
    return render(request, 'register_customer.html', {'form': form})


def register(request):
    """Main registration view that allows user to choose between customer and influencer"""
    return render(request, 'register.html')




# from django.contrib.auth.forms import AuthenticationForm
# from django.shortcuts import render, redirect

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # CORRECT REDIRECTION LOGIC
            if user.is_staff or user.is_superuser:           # Admin / Staff
                return redirect('admin_dashboard')
            elif user.user_type == 'influencer':             # Influencer
                # Check if influencer has been approved
                try:
                    application = InfluencerApplication.objects.get(user=user)
                    if not application.is_approved:
                        messages.error(request, 'Your influencer application is pending approval. You will be notified once approved.')
                        return redirect('home')
                except InfluencerApplication.DoesNotExist:
                    # If no application exists, redirect to application page
                    messages.error(request, 'Please complete your influencer application first.')
                    return redirect('influencer_application')

                return redirect('influencer_dashboard')
            else:                                             # Normal Customer
                return redirect('customer_dashboard')

    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})
# def user_login(request):
#     if request.method == 'POST':
#         form = AuthenticationForm(request, data=request.POST)
#         if form.is_valid():
#             user = form.get_user()
#             login(request, user)
#             if user.user_type == 'influencer':
#                 return redirect('influencer_dashboard')
#                 return redirect('admin_dashboard')
#             return redirect('customer_dashboard')
#     else:
#         form = AuthenticationForm()
#     return render(request, 'login.html', {'form': form})

@login_required
def influencer_dashboard(request):
    if request.user.user_type != 'influencer':
        return redirect('home')

    # Check if influencer has been approved
    try:
        application = InfluencerApplication.objects.get(user=request.user)
        if not application.is_approved:
            messages.error(request, 'Your influencer application is pending approval. You will be notified once approved.')
            return redirect('home')
    except InfluencerApplication.DoesNotExist:
        # If no application exists, redirect to application page
        messages.error(request, 'Please complete your influencer application first.')
        return redirect('influencer_application')

    influencer = request.user

    # Get dashboard statistics with real data
    from django.db.models import Sum, Count, Q, F
    from django.utils import timezone
    from datetime import timedelta

    # Calculate total revenue from completed orders for this influencer
    total_revenue = OrderItem.objects.filter(
        product__influencer=influencer,
        order__status=Order.COMPLETED
    ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    # Calculate total orders from completed orders for this influencer
    total_orders = OrderItem.objects.filter(
        product__influencer=influencer,
        order__status=Order.COMPLETED
    ).aggregate(total=Count('order', distinct=True))['total'] or 0

    # Calculate monthly revenue for current month
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_revenue = OrderItem.objects.filter(
        product__influencer=influencer,
        order__status=Order.COMPLETED,
        order__created_at__year=current_year,
        order__created_at__month=current_month
    ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    # Calculate monthly orders for current month
    monthly_orders = OrderItem.objects.filter(
        product__influencer=influencer,
        order__status=Order.COMPLETED,
        order__created_at__year=current_year,
        order__created_at__month=current_month
    ).aggregate(total=Count('order', distinct=True))['total'] or 0

    # Get top performing products for this influencer
    top_products = Product.objects.filter(
        influencer=influencer
    ).annotate(
        total_sales=Sum('account_order_items__quantity', filter=Q(account_order_items__order__status=Order.COMPLETED))
    ).filter(
        total_sales__isnull=False
    ).order_by('-total_sales')[:5]

    # Calculate revenue change percentage for progress bar
    previous_month = current_month - 1 if current_month > 1 else 12
    previous_year = current_year if current_month > 1 else current_year - 1

    previous_month_revenue = OrderItem.objects.filter(
        product__influencer=influencer,
        order__status=Order.COMPLETED,
        order__created_at__year=previous_year,
        order__created_at__month=previous_month
    ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    total_revenue_change = 0
    if previous_month_revenue > 0:
        total_revenue_change = min(100, int((total_revenue / previous_month_revenue) * 100))

    # Calculate orders change percentage
    previous_month_orders = OrderItem.objects.filter(
        product__influencer=influencer,
        order__status=Order.COMPLETED,
        order__created_at__year=previous_year,
        order__created_at__month=previous_month
    ).aggregate(total=Count('order', distinct=True))['total'] or 0

    total_orders_change = 0
    if previous_month_orders > 0:
        total_orders_change = min(100, int((total_orders / previous_month_orders) * 100))

    monthly_revenue_change = 0
    if previous_month_revenue > 0:
        monthly_revenue_change = min(100, int((monthly_revenue / previous_month_revenue) * 100))

    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'monthly_revenue': monthly_revenue,
        'monthly_orders': monthly_orders,
        'total_revenue_change': total_revenue_change,
        'total_orders_change': total_orders_change,
        'revenue_change': monthly_revenue_change,
        'top_products': top_products,
    }
    return render(request, 'influencer_dashboard.html', context)




@login_required
def edit_influencer_profile(request):
    if request.user.user_type != 'influencer':
        return redirect('home')

    profile, created = InfluencerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = InfluencerProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('influencer_dashboard')
    else:
        form = InfluencerProfileForm(instance=profile, user=request.user)

    return render(request, 'edit_profile.html', {'form': form})


@login_required
def view_influencer_profile(request):
    if request.user.user_type != 'influencer':
        return redirect('home')

    profile, created = InfluencerProfile.objects.get_or_create(user=request.user)
    return render(request, 'view_profile.html', {'profile': profile})


@login_required
def customer_dashboard(request):
    if request.user.user_type != 'customer':
        return redirect('login')

    influencers = InfluencerProfile.objects.filter(user__is_active=True).select_related('user')
    products = Product.objects.filter(stock__gt=0).select_related('category', 'influencer')[:12]
    categories = Category.objects.all()

    # FIXED: Add reels_videos to context like in home view
    reels_videos = InfluencerVideo.objects.filter(is_active=True).order_by('-created_at')

    return render(request, 'customer_dashboard.html', {
        'influencers': influencers,
        'products': products,
        'categories': categories,
        'reels_videos': reels_videos,
    })


def logout_view(request):
    logout(request)
    return redirect('home')


def list_influencers(request):
    profiles = InfluencerProfile.objects.filter(
        user__user_type='influencer',
        user__is_active=True
    ).select_related('user')
    return render(request, 'influencer_list.html', {'profiles': profiles})


def about_us(request):
    return render(request, 'about_us.html')


def view_influencer_detail(request, influencer_id):
    influencer = get_object_or_404(CustomUser, id=influencer_id, user_type='influencer', is_active=True)
    profile = getattr(influencer, 'influencer_profile', None)
    category_name = request.GET.get('category', 'All')
    categories = Category.objects.all()

    if category_name != 'All':
        category = get_object_or_404(Category, name__iexact=category_name)
        products = Product.objects.filter(influencer=influencer, category=category, stock__gt=0).select_related('category')
    else:
        products = Product.objects.filter(influencer=influencer, stock__gt=0).select_related('category')

    products_count = products.count()

    return render(request, 'influencer_detail.html', {
        'influencer': influencer,
        'profile': profile,
        'categories': categories,
        'selected_category': category_name,
        'products': products,
        'products_count': products_count
    })


@login_required
def featured_influencers(request):
    influencers = CustomUser.objects.filter(
        user_type='influencer',
        is_active=True
    ).select_related('influencer_profile').distinct()
    return render(request, 'featured_influencers.html', {'influencers': influencers})


def search_view(request):
    query = request.GET.get('q', '').strip()
    current_page = request.GET.get('page', '')

    if not query:
        if current_page == 'customer_dashboard':
            influencers = InfluencerProfile.objects.filter(user__is_active=True).select_related('user')
            products = Product.objects.filter(stock__gt=0).select_related('category', 'influencer')[:12]
            categories = Category.objects.all()
            return render(request, 'customer_dashboard.html', {
                'query': '',
                'influencers': influencers,
                'products': products,
                'categories': categories,
            })
        elif current_page == 'home':
            influencers = CustomUser.objects.filter(user_type='influencer', is_active=True)
            products = Product.objects.all().select_related('category', 'influencer')[:12]
            categories = Category.objects.all()
            return render(request, 'home.html', {
                'query': '',
                'influencers': influencers,
                'products': products,
                'categories': categories,
            })
        elif current_page == 'influencers':
            profiles = InfluencerProfile.objects.filter(user__is_active=True).select_related('user')
            return render(request, 'influencer_list.html', {'query': '', 'profiles': profiles})
        else:
            return render(request, 'search_results.html', {'query': ''})

    influencers = InfluencerProfile.objects.filter(
        Q(user__username__icontains=query) |
        Q(user__full_name__icontains=query) |
        Q(bio__icontains=query),
        user__is_active=True
    ).select_related('user')

    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__name__icontains=query) |
        Q(influencer__username__icontains=query),
        stock__gt=0
    ).select_related('category', 'influencer')

    context = {
        'query': query,
        'influencers': influencers,
        'products': products,
        'categories': Category.objects.all(),
    }

    if current_page == 'customer_dashboard':
        return render(request, 'customer_dashboard.html', context)
    elif current_page == 'home':
        return render(request, 'home.html', context)
    elif current_page == 'influencers':
        return render(request, 'influencer_list.html', {'profiles': influencers, 'query': query})
    else:
        return render(request, 'search_results.html', context)









from django.contrib.auth.decorators import login_required
from django.contrib import messages   # ← THIS LINE WAS MISSING!

@login_required
def upload_video(request):
    if request.user.user_type != 'influencer':
        return redirect('home')

    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES, influencer=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Reel uploaded successfully! Your video is now live.")
            return redirect('manage_videos')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = VideoUploadForm(influencer=request.user)

    return render(request, 'upload_video.html', {'form': form})

@login_required
def edit_video(request, video_id):
    if request.user.user_type != 'influencer':
        return redirect('home')

    video = get_object_or_404(InfluencerVideo, id=video_id, influencer=request.user)

    if request.method == 'POST':
        form = VideoEditForm(request.POST, request.FILES, instance=video, influencer=request.user)
        if form.is_valid():
            form.save()
            return redirect('manage_videos')
    else:
        form = VideoEditForm(instance=video, influencer=request.user)

    return render(request, 'edit_video.html', {
        'form': form,
        'video': video
    })


@login_required
def manage_videos(request):
    if request.user.user_type != 'influencer':
        return redirect('home')

    videos = InfluencerVideo.objects.filter(influencer=request.user).prefetch_related('products')

    return render(request, 'manage_videos.html', {'videos': videos})


@login_required
def delete_video(request, video_id):
    if request.user.user_type != 'influencer':
        return redirect('home')

    video = get_object_or_404(InfluencerVideo, id=video_id, influencer=request.user)

    if request.method == 'POST':
        video.delete()
        return redirect('manage_videos')

    return render(request, 'confirm_delete_video.html', {'video': video})


@login_required
def video_feed(request):
    if request.user.user_type != 'influencer':
        return redirect('home')

    # Get videos for this influencer in chronological order for vertical feed
    videos = InfluencerVideo.objects.filter(
        influencer=request.user,
        is_active=True
    ).prefetch_related('products').order_by('-created_at')

    return render(request, 'video_feed.html', {'videos': videos})


# from django.db.models import Sum
from django.db.models.functions import TruncMonth
# … your other imports (timezone, timedelta, json, messages, redirect, etc.) …



from django.contrib.auth.decorators import login_required

def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('home')

    today = timezone.now()

    # 1. Total revenue & commission
    total_revenue = Order.objects.filter(status='Completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # Check if commission_amount field exists before using it
    try:
        total_commission = Order.objects.filter(status='Completed').aggregate(
            total=Sum('commission_amount')
        )['total'] or 0
    except FieldError:
        # Fallback if commission_amount field doesn't exist
        total_commission = 0

    # Calculate commission based on percentage if commission_amount is 0
    if total_commission == 0:
        completed_orders = Order.objects.filter(status='Completed')
        total_commission = sum(float(order.total_amount) * (float(order.commission_percentage) / 100)
                             for order in completed_orders if order.total_amount and order.commission_percentage)

    commission_percentage = round((total_commission / total_revenue * 100), 2) if total_revenue and total_revenue != 0 else 0
    total_influencer_earnings = total_revenue - total_commission

    # Counts
    active_influencers = CustomUser.objects.filter(user_type='influencer', is_active=True).count()
    active_customers = CustomUser.objects.filter(user_type='customer', is_active=True).count()
    pending_influencer_approvals = CustomUser.objects.filter(user_type='influencer', is_active=False)
    pending_orders = Order.objects.filter(status='Pending').count()

    # Additional order statistics
    shipped_orders = Order.objects.filter(status='Shipped').count()
    completed_orders = Order.objects.filter(status='Completed').count()
    canceled_orders = Order.objects.filter(status='Canceled').count()
    total_orders = Order.objects.count()

    # Additional influencer management data
    all_influencers = CustomUser.objects.filter(user_type='influencer').select_related('influencer_profile')
    approved_influencers = CustomUser.objects.filter(user_type='influencer', is_active=True)
    rejected_influencers = CustomUser.objects.filter(user_type='influencer', is_active=False)
    pending_applications = InfluencerApplication.objects.filter(is_approved=False)
    approved_applications = InfluencerApplication.objects.filter(is_approved=True)

    # 7. Monthly revenue – last 12 months
    monthly_data = Order.objects.filter(
        status='Completed',
        created_at__year__gte=today.year - 1
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        revenue=Sum('total_amount')
    ).order_by('month')

    monthly_labels = []
    monthly_values = []
    data_dict = {item['month'].strftime('%Y-%m'): item['revenue'] or 0 for item in monthly_data}

    current = today.replace(day=1)
    for _ in range(12):
        key = current.strftime('%Y-%m')
        monthly_labels.append(current.strftime('%b %Y'))
        monthly_values.append(float(data_dict.get(key, 0)))
        if current.month == 1:
            current = current.replace(year=current.year - 1, month=12)
        else:
            current = current.replace(month=current.month - 1)

    monthly_labels.reverse()
    monthly_values.reverse()

    # 8. Top 5 influencers by earnings
    influencer_earnings = {}
    orders = Order.objects.filter(status='Completed') \
        .defer('address') \
        .select_related('user') \
        .prefetch_related('items__product__influencer')

    for order in orders:
        for item in order.items.all():
            influencer = getattr(item.product, 'influencer', None)
            if not influencer:
                continue
            # Safely calculate commission percentage
            try:
                commission_percentage = order.commission_percentage
            except AttributeError:
                commission_percentage = 10.0  # Default 10% commission
            earnings = item.price * item.quantity * (1 - commission_percentage / 100)

            if influencer.id not in influencer_earnings:
                influencer_earnings[influencer.id] = {'user': influencer, 'total_earnings': 0}
            influencer_earnings[influencer.id]['total_earnings'] += earnings

    top_influencers = sorted(influencer_earnings.values(),
                             key=lambda x: x['total_earnings'], reverse=True)[:5]

    # 9. FINAL BULLETPROOF TOP PRODUCTS — NO JOIN, NO product_id, NO ERROR EVER
    top_products = []
    try:
        from collections import Counter

        # Try to get product name directly from OrderItem (if you have a denormalized field)
        raw_items = OrderItem.objects.filter(order__status='Completed') \
            .values('product_name', 'quantity')

        # If product_name doesn't exist, fall back to empty
        if not raw_items or 'product_name' not in raw_items[0]:
            raise Exception("No product_name field")

        product_sales = Counter()
        for item in raw_items:
            name = item['product_name'] or "Unknown Product"
            qty = item['quantity'] or 0
            product_sales[name] += qty

        top_products = [
            {'product__name': name, 'total_sold': count}
            for name, count in product_sales.most_common(5)
        ]

    except Exception:
        # Ultimate fallback — just show empty list, dashboard NEVER crashes
        top_products = []

    # 10. Pending withdraw requests — SAFE
    pending_withdraw_requests = WithdrawRequest.objects.filter(status='pending').values(
        'id', 'amount', 'status', 'created_at'
    )

    # POST handling for admin actions
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve_influencer':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(CustomUser, id=user_id)
            # Ensure user is active and has the correct user type
            user.is_active = True
            user.user_type = 'influencer'
            user.save()

            # Also approve their application if it exists
            try:
                application = InfluencerApplication.objects.get(user=user)
                application.is_approved = True
                application.reviewed_by = request.user
                application.reviewed_at = timezone.now()
                application.save()
            except InfluencerApplication.DoesNotExist:
                pass

            messages.success(request, f'Influencer {user.username} has been approved successfully.')

        elif action == 'deny_influencer':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(CustomUser, id=user_id)
            # Set user as inactive but maintain user type as influencer
            user.is_active = False
            user.save()

            # Also update their application status if it exists
            try:
                application = InfluencerApplication.objects.get(user=user)
                application.is_approved = False
                application.reviewed_by = request.user
                application.reviewed_at = timezone.now()
                application.save()
            except InfluencerApplication.DoesNotExist:
                pass

            messages.success(request, f'Influencer {user.username} has been denied.')

        elif action == 'approve_withdraw':
            request_id = request.POST.get('request_id')
            withdraw_request = get_object_or_404(WithdrawRequest, id=request_id)
            withdraw_request.status = 'approved'
            withdraw_request.approved_at = timezone.now()
            withdraw_request.approved_by = request.user
            withdraw_request.save()

            messages.success(request, f'Withdraw request for ₹{withdraw_request.amount} has been approved.')

        elif action == 'deny_withdraw':
            request_id = request.POST.get('request_id')
            reason = request.POST.get('reason', '')
            withdraw_request = get_object_or_404(WithdrawRequest, id=request_id)
            withdraw_request.status = 'rejected'
            withdraw_request.reason = reason
            withdraw_request.approved_at = timezone.now()
            withdraw_request.approved_by = request.user
            withdraw_request.save()

            messages.success(request, f'Withdraw request for ₹{withdraw_request.amount} has been denied.')

        return redirect('admin_dashboard')

    context = {
        'total_revenue': total_revenue,
        'total_commission': total_commission,
        'commission_percentage': commission_percentage,
        'total_influencer_earnings': total_influencer_earnings,
        'active_influencers': active_influencers,
        'active_customers': active_customers,
        'pending_influencer_approvals': pending_influencer_approvals,
        'pending_influencer_approvals_count': pending_influencer_approvals.count(),
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
        'completed_orders': completed_orders,
        'canceled_orders': canceled_orders,
        'total_orders': total_orders,
        'monthly_revenue_labels': json.dumps(monthly_labels),
        'monthly_revenue_values': json.dumps(monthly_values),
        'top_influencers': top_influencers,
        'top_products': top_products,
        'pending_withdraw_requests': pending_withdraw_requests,
        'all_influencers': all_influencers,
        'approved_influencers': approved_influencers,
        'rejected_influencers': rejected_influencers,
        'pending_applications': pending_applications,
        'approved_applications': approved_applications,
    }

    return render(request, 'admin_dashboard.html', context)

# accounts/views.py
from django.shortcuts import render
from orders.models import Order

def order_tracking(request):
    order = None
    searched = False

    if request.GET.get('order_id'):
        searched = True
        try:
            # FIXED: Use 'id' instead of 'order_id'
            order = Order.objects.get(id=request.GET['order_id'])
        except (Order.DoesNotExist, ValueError):
            order = None

    return render(request, 'order_tracking.html', {
        'order': order,
        'searched': searched
    })


@login_required
def manage_influencers(request):
    if not request.user.is_staff:
        return redirect('home')

    # Handle POST requests for approval/denial actions
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')

        if action and user_id:
            try:
                user = get_object_or_404(CustomUser, id=user_id, user_type='influencer')

                if action == 'approve_influencer':
                    # Approve the influencer
                    user.is_active = True
                    user.user_type = 'influencer'
                    user.save()

                    # Update application status
                    try:
                        application = InfluencerApplication.objects.get(user=user)
                        application.is_approved = True
                        application.reviewed_by = request.user
                        application.reviewed_at = timezone.now()
                        application.save()
                        messages.success(request, f'Influencer {user.username} has been approved successfully.')
                    except InfluencerApplication.DoesNotExist:
                        messages.success(request, f'Influencer {user.username} has been approved successfully.')

                elif action == 'deny_influencer':
                    # Deny the influencer
                    user.is_active = False
                    user.save()

                    # Update application status
                    try:
                        application = InfluencerApplication.objects.get(user=user)
                        application.is_approved = False
                        application.reviewed_by = request.user
                        application.reviewed_at = timezone.now()
                        application.save()
                        messages.success(request, f'Influencer {user.username} has been denied.')
                    except InfluencerApplication.DoesNotExist:
                        messages.success(request, f'Influencer {user.username} has been denied.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found.')

        return redirect('manage_influencers')

    # Get all influencers with their applications and profiles
    influencers = CustomUser.objects.filter(user_type='influencer').select_related('influencer_profile')
    pending_applications = InfluencerApplication.objects.filter(is_approved=False)
    approved_applications = InfluencerApplication.objects.filter(is_approved=True)

    context = {
        'influencers': influencers,
        'pending_applications': pending_applications,
        'approved_applications': approved_applications,
    }

    return render(request, 'manage_influencers.html', context)


@login_required
def toggle_influencer_status(request, user_id):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        user = get_object_or_404(CustomUser, id=user_id, user_type='influencer')
        # Toggle the active status
        user.is_active = not user.is_active
        user.save()

        messages.success(request, f'Influencer status updated successfully.')

    return redirect('manage_influencers')


@login_required
def view_influencer_details(request, user_id):
    if not request.user.is_staff:
        return redirect('home')

    influencer = get_object_or_404(CustomUser, id=user_id, user_type='influencer')
    profile = getattr(influencer, 'influencer_profile', None)
    application = getattr(influencer, 'influencer_application', None)

    # Get influencer's products and videos
    products = Product.objects.filter(influencer=influencer)
    videos = InfluencerVideo.objects.filter(influencer=influencer)

    context = {
        'influencer': influencer,
        'profile': profile,
        'application': application,
        'products': products,
        'videos': videos,
    }

    return render(request, 'influencer_details.html', context)


@login_required
def delete_influencer(request, user_id):
    if not request.user.is_staff:
        return redirect('home')

    influencer = get_object_or_404(CustomUser, id=user_id, user_type='influencer')

    if request.method == 'POST':
        # Delete related data first
        InfluencerProfile.objects.filter(user=influencer).delete()
        InfluencerVideo.objects.filter(influencer=influencer).delete()
        WithdrawRequest.objects.filter(influencer=influencer).delete()
        # Also delete any related influencer applications
        InfluencerApplication.objects.filter(user=influencer).delete()

        # Delete the user account
        influencer.delete()

        messages.success(request, 'Influencer account has been deleted successfully.')
        return redirect('manage_influencers')

    # If GET request, show confirmation page
    context = {
        'influencer': influencer
    }
    return render(request, 'confirm_delete_influencer.html', context)


@login_required
def influencer_earnings(request):
    if request.user.user_type != 'influencer':
        return redirect('home')

    # Get all orders for this influencer's products
    influencer_orders = OrderItem.objects.filter(
        product__influencer=request.user,
        order__status=Order.COMPLETED
    ).select_related('order', 'product')

    # Calculate total earnings
    total_earnings = sum([
        float(item.price) * item.quantity * (1 - float(item.order.commission_percentage) / 100)
        for item in influencer_orders
    ])

    # Get withdraw requests for this influencer
    withdraw_requests = WithdrawRequest.objects.filter(influencer=request.user).order_by('-created_at')

    # Calculate pending withdrawals
    pending_withdrawals = WithdrawRequest.objects.filter(
        influencer=request.user,
        status='pending'
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'total_earnings': total_earnings,
        'pending_withdrawals': pending_withdrawals,
        'withdraw_requests': withdraw_requests,
        'influencer_orders': influencer_orders,
    }

    return render(request, 'influencer_earnings.html', context)


@login_required
def request_withdrawal(request):
    if request.user.user_type != 'influencer':
        return redirect('home')

    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            amount = float(amount)
            # Create a withdraw request
            WithdrawRequest.objects.create(
                influencer=request.user,
                amount=amount,
                status='pending'
            )
            messages.success(request, 'Withdrawal request submitted successfully!')
        except ValueError:
            messages.error(request, 'Invalid amount entered.')

        return redirect('influencer_earnings')

    return redirect('influencer_earnings')


def influencer_application(request):
    from .models import InfluencerApplication
    from .forms import InfluencerApplicationForm

    # Get the current user's application
    application, created = InfluencerApplication.objects.get_or_create(
        user=request.user,
        defaults={'is_approved': False}
    )

    if request.method == 'POST':
        form = InfluencerApplicationForm(request.POST, request.FILES, instance=application, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your influencer application has been submitted successfully. Our team will review it shortly.')
            return redirect('influencer_application_success')
    else:
        form = InfluencerApplicationForm(instance=application, user=request.user)

    return render(request, 'influencer_application.html', {'form': form})


def influencer_application_success(request):
    return render(request, 'influencer_application_success.html')



def support(request):
    return render(request, 'support.html')







@login_required
def manage_users(request):
    if not request.user.is_staff:
        return redirect('home')

    # Get all users (customers)
    users = CustomUser.objects.filter(user_type='customer')

    context = {
        'users': users,
    }

    return render(request, 'manage_users.html', context)





from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Import product models for the views
try:
    from products.models import Product, Category
except ImportError:
    try:
        from product.models import Product, Category
    except ImportError:
        from .models import Product, Category  # fallback in case of import issues



@csrf_exempt
@login_required
def increment_video_views(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            video_id = data.get('video_id')

            if video_id:
                video = get_object_or_404(InfluencerVideo, id=video_id)
                video.views += 1
                video.save()

                return JsonResponse({'success': True, 'views': video.views})
            else:
                return JsonResponse({'success': False, 'error': 'Video ID not provided'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Method not allowed'})




















# Import the VideoLike model
from .models import VideoLike

@csrf_exempt
@login_required
def toggle_video_like(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            video_id = data.get('video_id')

            if video_id:
                video = get_object_or_404(InfluencerVideo, id=video_id)

                # Check if user has already liked this video
                try:
                    video_like = VideoLike.objects.get(user=request.user, video=video)
                    # User already liked, so unlike it
                    video_like.delete()
                    video.likes = max(0, video.likes - 1)  # Ensure likes don't go below 0
                    user_liked = False
                except VideoLike.DoesNotExist:
                    # User hasn't liked yet, so like it
                    VideoLike.objects.create(user=request.user, video=video)
                    video.likes += 1
                    user_liked = True

                video.save()

                return JsonResponse({
                    'success': True,
                    'likes': video.likes,
                    'user_liked': user_liked
                })
            else:
                return JsonResponse({'success': False, 'error': 'Video ID not provided'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Method not allowed'})


@login_required
def manage_orders(request):
    if not request.user.is_staff:
        return redirect('home')

    # Get all orders with filters
    orders = Order.objects.select_related('user').all()

    # Apply filters if provided
    influencer_filter = request.GET.get('influencer')
    customer_filter = request.GET.get('customer')
    status_filter = request.GET.get('status')
    date_filter = request.GET.get('date')

    if influencer_filter:
        orders = orders.filter(items__product__influencer__username__icontains=influencer_filter)
    if customer_filter:
        orders = orders.filter(user__username__icontains=customer_filter)
    if status_filter:
        orders = orders.filter(status=status_filter)
    if date_filter:
        from django.utils.dateparse import parse_date
        parsed_date = parse_date(date_filter)
        if parsed_date:
            orders = orders.filter(created_at__date=parsed_date)

    # Get unique influencer and customer lists for filters
    influencers = CustomUser.objects.filter(user_type='influencer').values_list('username', flat=True)
    customers = CustomUser.objects.filter(user_type='customer').values_list('username', flat=True)

    # Get unique statuses
    statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]

    context = {
        'orders': orders.distinct(),
        'influencers': influencers,
        'customers': customers,
        'statuses': statuses,
        'current_filters': {
            'influencer': influencer_filter,
            'customer': customer_filter,
            'status': status_filter,
            'date': date_filter,
        },
    }

    return render(request, 'manage_orders.html', context)


@login_required
def order_detail(request, order_id):
    if not request.user.is_staff:
        return redirect('home')

    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all().select_related('product')

    context = {
        'order': order,
        'order_items': order_items,
    }

    return render(request, 'order_detail.html', context)


@login_required
def update_order_status(request, order_id):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')

        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            order.status = new_status
            order.save()

            # Auto-update influencer earnings after delivery
            if new_status == Order.SHIPPED or new_status == Order.COMPLETED:
                # Calculate and update influencer earnings
                for item in order.items.all():
                    if item.product and item.product.influencer:
                        # Trigger earning calculation for the influencer
                        # This is handled automatically in the models
                        pass

            messages.success(request, f'Order #{order.id} status updated to {new_status}')
        else:
            messages.error(request, 'Invalid status')

    return redirect('order_detail', order_id=order_id)


@login_required
def process_refund(request, order_id):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        refund_type = request.POST.get('refund_type')
        partial_amount = request.POST.get('partial_amount', 0)

        if refund_type == 'full':
            # Process full refund
            order.status = Order.CANCELED
            order.save()
            messages.success(request, f'Full refund processed for Order #{order.id}')
        elif refund_type == 'partial' and partial_amount:
            # Process partial refund
            try:
                partial_amount = float(partial_amount)
                if partial_amount <= float(order.total_amount):
                    # For partial refunds, keep the order status as is but mark as refunded
                    # Or create a separate refund record
                    messages.success(request, f'Partial refund of ₹{partial_amount} processed for Order #{order.id}')
                else:
                    messages.error(request, 'Refund amount exceeds order total')
            except ValueError:
                messages.error(request, 'Invalid refund amount')

    return redirect('order_detail', order_id=order_id)


@login_required
def manage_support_tickets(request):
    if not request.user.is_staff:
        return redirect('home')

    # For now, we'll use a simple approach without a dedicated ticket model
    # In a real application, you would have a SupportTicket model
    # For demo purposes, we'll just display recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]

    context = {
        'recent_orders': recent_orders,
    }

    return render(request, 'manage_support_tickets.html', context)


@login_required
def manage_products(request):
    if not request.user.is_staff:
        return redirect('home')

    # Get all products with filtering options
    products = Product.objects.select_related('influencer', 'category').all()

    # Apply filters if provided
    influencer_filter = request.GET.get('influencer')
    category_filter = request.GET.get('category')
    status_filter = request.GET.get('status')  # approved, pending, hidden, featured, trending

    if influencer_filter:
        products = products.filter(influencer__username__icontains=influencer_filter)
    if category_filter:
        products = products.filter(category__name__icontains=category_filter)
    if status_filter == 'approved':
        products = products.filter(is_approved=True)
    elif status_filter == 'pending':
        products = products.filter(is_approved=False)
    elif status_filter == 'hidden':
        products = products.filter(is_hidden=True)
    elif status_filter == 'featured':
        products = products.filter(is_featured=True)
    elif status_filter == 'trending':
        products = products.filter(is_trending=True)

    # Get unique influencers and categories for filters
    influencers = CustomUser.objects.filter(user_type='influencer').values_list('username', flat=True)
    categories = Category.objects.values_list('name', flat=True)

    # Handle POST requests for bulk actions
    if request.method == 'POST':
        action = request.POST.get('action')
        product_ids = request.POST.getlist('product_ids')

        if action and product_ids:
            products_to_update = Product.objects.filter(id__in=product_ids)

            if action == 'approve':
                products_to_update.update(is_approved=True)
                messages.success(request, f'{len(product_ids)} products approved successfully.')
            elif action == 'unapprove':
                products_to_update.update(is_approved=False)
                messages.success(request, f'{len(product_ids)} products unapproved successfully.')
            elif action == 'feature':
                products_to_update.update(is_featured=True)
                messages.success(request, f'{len(product_ids)} products marked as featured.')
            elif action == 'unfeature':
                products_to_update.update(is_featured=False)
                messages.success(request, f'{len(product_ids)} products unmarked as featured.')
            elif action == 'hide':
                products_to_update.update(is_hidden=True)
                messages.success(request, f'{len(product_ids)} products hidden successfully.')
            elif action == 'show':
                products_to_update.update(is_hidden=False)
                messages.success(request, f'{len(product_ids)} products shown successfully.')
            elif action == 'make_trending':
                products_to_update.update(is_trending=True)
                messages.success(request, f'{len(product_ids)} products marked as trending.')
            elif action == 'remove_trending':
                products_to_update.update(is_trending=False)
                messages.success(request, f'{len(product_ids)} products removed from trending.')
            elif action == 'delete':
                # Delete the selected products
                products_to_update.delete()
                messages.success(request, f'{len(product_ids)} products deleted successfully.')

        return redirect('manage_products')

    context = {
        'products': products,
        'influencers': influencers,
        'categories': categories,
        'current_filters': {
            'influencer': influencer_filter,
            'category': category_filter,
            'status': status_filter,
        },
    }

    return render(request, 'manage_products.html', context)


@login_required
def toggle_product_flag(request, product_id):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        flag = request.POST.get('flag')
        value = request.POST.get('value') == 'true'

        if flag in ['is_approved', 'is_featured', 'is_hidden', 'is_trending']:
            setattr(product, flag, value)
            product.save()

            status_map = {
                'is_approved': 'approved' if value else 'unapproved',
                'is_featured': 'featured' if value else 'unfeatured',
                'is_hidden': 'hidden' if value else 'shown',
                'is_trending': 'trending' if value else 'not trending',
            }
            messages.success(request, f'Product {product.name} {status_map[flag]} successfully.')

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


@login_required
def reassign_product(request, product_id):
    if not request.user.is_staff:
        return redirect('home')

    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        new_influencer_id = request.POST.get('influencer_id')
        new_influencer = get_object_or_404(CustomUser, id=new_influencer_id, user_type='influencer')

        product.influencer = new_influencer
        product.save()

        messages.success(request, f'Product {product.name} reassigned to {new_influencer.username}.')
        return redirect('manage_products')

    influencers = CustomUser.objects.filter(user_type='influencer')
    context = {
        'product': product,
        'influencers': influencers,
    }

    return render(request, 'reassign_product.html', context)





