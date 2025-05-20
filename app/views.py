from django.shortcuts import render, get_object_or_404, redirect
from .models import Product , OrderDetail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.http import JsonResponse , HttpResponseNotFound
from django.db.models import Sum
import stripe, json
import datetime
from .forms import ProductForm , UserRegistrationForm
def index(request):
    products = Product.objects.all()
    return render(request, 'app/index.html' , {'products': products})

def detail(request,product_id):
    product = Product.objects.get(id=product_id)
    stripe_publishable_key = settings.STRIPE_PUBLISHABLE_KEY
    return render(request, 'app/detail.html', {'product': product, 'stripe_publishable_key': stripe_publishable_key})

@csrf_exempt
def create_checkout_session(request, product_id):
    try:
        request_data = json.loads(request.body)
        product = get_object_or_404(Product, id=product_id)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        checkout_session = stripe.checkout.Session.create(
            customer_email=request_data['email'],
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': product.name,
                        },
                        'unit_amount': int(product.price * 100),
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=request.build_absolute_uri(reverse('success')) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse('failed')),
        )

        order = OrderDetail()
        order.customer_email = request_data['email']
        order.Product = product
        order.stripe_payment_intent = checkout_session.id
        order.amount = int(product.price)
        order.save()

        return JsonResponse({'sessionid': checkout_session.id})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except stripe.error.StripeError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def payment_success_view(request):
    session_id = request.GET.get('session_id')
    if session_id is None:
        return HttpResponseNotFound('Session ID not found')
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        order = get_object_or_404(OrderDetail, stripe_payment_intent=session_id)
        order.has_paid = True
        order.save()
        return render(request, 'app/payment_success.html', {'order': order})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def payment_failed_view(request):
    return render(request, 'app/payment_failed.html')

def create_product(request):
    if request.method =='POST':
        product_form = ProductForm(request.POST, request.FILES)
        if product_form.is_valid():
            new_product = product_form.save(commit=False)
            new_product.seller = request.user
            new_product.save()
            return redirect('dashboard')
    product_form = ProductForm()
    return render(request, 'app/create_product.html', {'product_form': product_form})


def product_edit(request, product_id):
    product = Product.objects.get(id=product_id)
    if product.seller != request.user:
        return redirect('invalid')
    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES, instance=product)
        if product_form.is_valid():
            product_form.save()
            return redirect('dashboard')
    else:
        product_form = ProductForm(instance=product)  
    return render(request, 'app/product_edit.html', {'product_form': product_form, 'product': product})


def product_delete(request, product_id):
    product = Product.objects.get(id=product_id)
    if product.seller != request.user:
        return redirect('invalid')
    
    if request.method == 'POST':
        product.delete()
        return redirect('index')
    return render(request, 'app/product_delete.html', {'product': product})

def dashboard(request):
    products = Product.objects.all()
    return render(request, 'app/dashboard.html', {'products': products})

def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()
            return redirect('index')
    else:
        user_form = UserRegistrationForm()
    return render(request, 'app/register.html', {'user_form': user_form})

def invalid(request):
    return render(request, 'app/invalid.html')


def my_purchases(request):
    orders = OrderDetail.objects.filter(
        customer_email=request.user.email,
        has_paid=True
    ).order_by('-created_at')
    return render(request, 'app/purchases.html', {'orders': orders})

def sales(request):
    orders = OrderDetail.objects.filter(
        Product__seller=request.user,
        has_paid=True
    )
    
    total_sales = orders.aggregate(Sum('amount'))
    
    # 365 day sales sum
    last_year = datetime.date.today() - datetime.timedelta(days=365)
    yearly_data = orders.filter(created_at__gt=last_year)
    yearly_sales = yearly_data.aggregate(Sum('amount'))
    
    # 30 day sales sum
    last_month = datetime.date.today() - datetime.timedelta(days=30)
    monthly_data = orders.filter(created_at__gt=last_month)
    monthly_sales = monthly_data.aggregate(Sum('amount'))
    
    # 7 day sales sum
    last_week = datetime.date.today() - datetime.timedelta(days=7)
    weekly_data = orders.filter(created_at__gt=last_week)
    weekly_sales = weekly_data.aggregate(Sum('amount'))
    
    # Daily sales for the past 30 days
    daily_sales_sums = orders.filter(
        created_at__gt=last_month
    ).values('created_at__date').order_by('created_at__date').annotate(sum=Sum('amount'))
    
    # Product-wise sales
    product_sales_sums = orders.values('Product__name').order_by('Product__name').annotate(sum=Sum('amount'))
    
    return render(request, 'app/sales.html', {
        'total_sales': total_sales,
        'yearly_sales': yearly_sales,
        'monthly_sales': monthly_sales,
        'weekly_sales': weekly_sales,
        'daily_sales_sums': daily_sales_sums,
        'product_sales_sums': product_sales_sums
    })