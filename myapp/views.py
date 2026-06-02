# django_configs/views.py
# Paste this file or add these views inside your Django app's views.py.

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from .forms import LoginForm, SignupForm, BecomeWorkerForm

User = get_user_model()

def ensure_seeded_workers():
    # Seeding disabled by request. Only real workers from the database are utilized.
    pass

from django.apps import apps
import re

def get_app_models():
    """Dynamically locates and returns references to the exact custom database models."""
    custom_models = {
        'City': None,
        'Category': None,
        'WorkerProfile': None,
        'WorkerCategory': None,
        'BookingRequest': None,
        'Review': None,
        'ContactMessage': None,
    }
    for app_config in apps.get_app_configs():
        for model_name, model_cls in app_config.models.items():
            name_lower = model_name.lower()
            if name_lower == 'city':
                custom_models['City'] = model_cls
            elif name_lower == 'category':
                custom_models['Category'] = model_cls
            elif name_lower == 'workerprofile':
                custom_models['WorkerProfile'] = model_cls
            elif name_lower == 'workercategory':
                custom_models['WorkerCategory'] = model_cls
            elif name_lower == 'bookingrequest':
                custom_models['BookingRequest'] = model_cls
            elif name_lower == 'review':
                custom_models['Review'] = model_cls
            elif name_lower == 'contactmessage':
                custom_models['ContactMessage'] = model_cls
    return custom_models

def get_user_booking_counts(request):
    """Calculates and returns (pending_bookings_count, pending_sent_bookings_count) and manages sessions."""
    pending_bookings_count = 0
    pending_sent_bookings_count = 0
    if request.user.is_authenticated:
        try:
            models = get_app_models()
            BookingRequest = models.get('BookingRequest')
            if BookingRequest:
                pending_bookings_count = BookingRequest.objects.filter(worker__user=request.user, status='pending').count()
                pending_sent_bookings_count = BookingRequest.objects.filter(client=request.user).exclude(status='completed').count()
                
                # Check for updates and reset "bookings_viewed" if there is a new pending item
                last_seen_pending = request.session.get('last_seen_pending_count', 0)
                last_seen_sent = request.session.get('last_seen_sent_count', 0)
                
                if pending_bookings_count > last_seen_pending or pending_sent_bookings_count > last_seen_sent:
                    request.session['bookings_viewed'] = False
        except Exception as e:
            print(f"DEBUG Error in get_user_booking_counts: {e}")
            
    return pending_bookings_count, pending_sent_bookings_count

def parse_experience_years(exp_str):
    if not exp_str:
        return 0
    match = re.search(r'\d+', str(exp_str))
    if match:
        return int(match.group())
    return 0

def find_workers(request):
    """Find Workers / Home Page View with search, category, city, and status filters"""
    # Debug reviews dump
    try:
        models_dbg = get_app_models()
        Review_dbg = models_dbg.get('Review')
        if Review_dbg:
            import os
            dbg_path = os.path.join(os.path.dirname(__file__), 'all_reviews_debug.txt')
            with open(dbg_path, 'w') as f_dbg:
                f_dbg.write(f"Total reviews in database: {Review_dbg.objects.all().count()}\n")
                for r in Review_dbg.objects.all():
                    f_dbg.write(f"ID: {r.id} | Rating: {r.rating} ({type(r.rating)}) | Comment: {r.comment}\n")
    except Exception as d_err:
        print(f"DEBUG info error in find_workers: {d_err}")

    category_filter = request.GET.get('category', 'All')
    city_filter = request.GET.get('city', '')
    search_filter = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    models = get_app_models()
    Category = models['Category']
    City = models['City']
    WorkerProfile = models['WorkerProfile']
    Review = models.get('Review')

    # 1. Resolve Category choices
    category_options = []
    if Category:
        try:
            db_cats = Category.objects.filter(is_active=True).order_by('name')
            icons_map = {
                'plumber': 'ti-droplet',
                'electrician': 'ti-bolt',
                'painter': 'ti-brush',
                'mechanic': 'ti-tool',
                'labour': 'ti-hammer',
                'carpenter': 'ti-axe',
            }
            for cat in db_cats:
                icon = cat.icon or icons_map.get(cat.name.lower(), 'ti-category-2')
                category_options.append((cat.name, cat.name, icon))
        except Exception:
            pass
        
    if category_options:
        # Move 'Other' category option to the end
        cats_non_other = [cat for cat in category_options if cat[0].lower() != 'other']
        cats_other = [cat for cat in category_options if cat[0].lower() == 'other']
        category_options = cats_non_other + cats_other
    else:
        category_options = [
            ('Plumber', 'Plumber', 'ti-droplet'),
            ('Electrician', 'Electrician', 'ti-bolt'),
            ('Painter', 'Painter', 'ti-brush'),
            ('Mechanic', 'Mechanic', 'ti-tool'),
            ('Labour', 'Labour', 'ti-hammer'),
            ('Carpenter', 'Carpenter', 'ti-axe'),
            ('Other', 'Other Service', 'ti-category-2'),
        ]
    
    # Prepend 'All' option for category tabs row
    category_options.insert(0, ('All', 'All Items', 'ti-layout-grid'))

    # 2. Resolve City choices
    city_choices = []
    if City:
        try:
            db_cities = City.objects.filter(is_active=True).order_by('name')
            for city in db_cities:
                city_choices.append((city.name, city.name))
        except Exception:
            pass
        
    if not city_choices:
        city_choices = [
            ('Lahore', 'Lahore'),
            ('Karachi', 'Karachi'),
            ('Islamabad', 'Islamabad'),
            ('Rawalpindi', 'Rawalpindi'),
        ]
    
    # Re-order to place any 'Other' city choices at the end
    cities_non_other = [c for c in city_choices if c[0].lower() != 'other']
    cities_other = [c for c in city_choices if c[0].lower() == 'other']
    city_choices = cities_non_other + cities_other

    if not any(c[0].lower() == 'other' for c in city_choices):
        city_choices.append(('Other', 'Other City'))

    # 3. Pull real workers from custom database Models
    real_workers = []
    if WorkerProfile:
        try:
            # Sync any User registered as is_worker=True who does not yet have a WorkerProfile
            for u in User.objects.filter(is_worker=True):
                if not hasattr(u, 'worker_profile'):
                    WorkerProfile.objects.get_or_create(user=u)

            profiles = WorkerProfile.objects.select_related('user', 'city').prefetch_related('categories').all()
            for p in profiles:
                u = p.user
                name = getattr(u, 'name', '') or getattr(u, 'username', '') or u.email
                initials = ''.join([part[0].upper() for part in name.split()[:2]]) if len(name.split()) >= 2 else name[:2].upper()
                if not initials:
                    initials = 'SP'
                
                # Fetch categories
                p_categories = list(p.categories.all())
                category_name = p_categories[0].name if p_categories else 'Other'
                
                # Fetch city name
                city_name = p.city.name if p.city else 'Other'
                
                # Compute status
                status_str = 'Busy' if not p.is_available else 'Available'
                
                # Calculate real rating
                calculated_rating = 0.0
                if Review:
                    try:
                        p_reviews = Review.objects.filter(reviewee=u)
                        p_reviews_count = p_reviews.count()
                        if p_reviews_count > 0:
                            calculated_rating = round(sum(r.rating for r in p_reviews) / p_reviews_count, 1)
                    except Exception:
                        pass
                
                real_workers.append({
                    'id': str(p.id),
                    'name': name,
                    'initials': initials,
                    'category': category_name,
                    'city': city_name,
                    'rating': str(calculated_rating),
                    'is_verified': p.is_verified,
                    'bio': p.bio or "Specialized domestic technician. Friendly service and professional results guaranteed.",
                    'experience': f"{p.experience_years} year" if p.experience_years == 1 else f"{p.experience_years} years",
                    'status': status_str,
                    'is_current_user': request.user.is_authenticated and (str(u.id) == str(request.user.id))
                })
        except Exception:
            pass

    all_workers = real_workers

    # Apply Category Filter
    if category_filter and category_filter != 'All':
        all_workers = [w for w in all_workers if w['category'].lower() == category_filter.lower()]

    # Apply City Filter
    if city_filter:
        all_workers = [w for w in all_workers if w['city'].lower() == city_filter.lower()]

    # Apply Status Filter
    if status_filter:
        all_workers = [w for w in all_workers if w.get('status', 'Available').lower() == status_filter.lower()]

    # Apply Search Filter
    if search_filter:
        search_term = search_filter.strip().lower()
        all_workers = [
            w for w in all_workers if (
                search_term in w['name'].lower() or
                search_term in w['category'].lower() or
                search_term in w['city'].lower() or
                search_term in w['bio'].lower()
            )
        ]

    pending_bookings_count, pending_sent_count = get_user_booking_counts(request)

    return render(request, 'find_workers.html', {
        'workers': all_workers,
        'workers_count': len(all_workers),
        'category_options': category_options,
        'city_choices': city_choices,
        'current_category': category_filter,
        'current_city': city_filter,
        'current_status': status_filter,
        'current_search': search_filter,
        'pending_bookings_count': pending_bookings_count,
    })

def my_bookings(request):
    """Client & Worker Bookings/Proposals Tracker View (Direct Database Connected)"""
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to view and manage bookings.")
        return redirect('login')

    models = get_app_models()
    WorkerProfile = models['WorkerProfile']
    BookingRequest = models['BookingRequest']
    City = models['City']
    Category = models['Category']

    status_map_to_db = {
        'Pending': 'pending',
        'Accepted': 'accepted',
        'Declined': 'rejected',
        'Completed': 'completed',
    }

    status_map_to_ui = {
        'pending': 'Pending',
        'accepted': 'Accepted',
        'rejected': 'Declined',
        'completed': 'Completed',
    }

    # Handle direct callback booking actions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # ─── CASE A: CREATE NEW PROPOSAL ───
        if action == 'create':
            worker_id = request.POST.get('worker_id')
            notes = request.POST.get('notes', '')
            
            # Resolve WorkerProfile
            worker_profile_obj = None
            if WorkerProfile:
                try:
                    worker_profile_obj = WorkerProfile.objects.get(id=worker_id)
                except (WorkerProfile.DoesNotExist, ValueError):
                    pass
                if not worker_profile_obj:
                    try:
                        worker_profile_obj = WorkerProfile.objects.get(user_id=worker_id)
                    except (WorkerProfile.DoesNotExist, ValueError):
                        pass
                
            if not worker_profile_obj:
                messages.error(request, "Worker profile not found in system.")
                return redirect('find_workers')

            # CRITICAL SECURITY RULE: Specialist cannot book themselves
            if request.user == worker_profile_obj.user:
                messages.error(request, "Security lock: You cannot send a booking proposal to your own account.")
                return redirect('find_workers')
                
            if BookingRequest:
                try:
                    BookingRequest.objects.create(
                        client=request.user,
                        worker=worker_profile_obj,
                        description=notes,
                        status='pending'
                    )
                    messages.success(request, f"Your service proposal was successfully sent to {worker_profile_obj.user.name}!")
                except Exception as e:
                    messages.error(request, f"Error saving booking request: {str(e)}")
            else:
                messages.error(request, "Database Error: The BookingRequest model was not detected.")
                
            return redirect('my_bookings')
            
        # ─── CASE B: RESPONSE (WORKER DECISION RESOLUTION) ───
        elif action == 'respond':
            booking_id = request.POST.get('booking_id')
            new_status = request.POST.get('status') # 'Accepted', 'Declined', 'Completed'
            
            if BookingRequest:
                try:
                    bk = BookingRequest.objects.get(id=booking_id)
                    is_authorized = False
                    
                    # Ensure user owns either client side or worker side of booking
                    # Exception: client cannot mark a job as Completed! Only the worker!
                    if new_status == 'Completed':
                        is_authorized = (bk.worker and bk.worker.user == request.user)
                    else:
                        is_authorized = (bk.worker and bk.worker.user == request.user) or bk.client == request.user
                        
                    if is_authorized:
                        # Direct method calls based on exact target flows of model
                        if new_status == 'Accepted' and hasattr(bk, 'accept'):
                            bk.accept()
                            messages.success(request, "Proposal successfully accepted! Callback initiated.")
                        elif new_status == 'Declined' and hasattr(bk, 'reject'):
                            bk.reject()
                            messages.success(request, "Proposal successfully declined.")
                        elif new_status == 'Completed' and hasattr(bk, 'mark_complete'):
                            bk.mark_complete()
                            messages.success(request, "Task successfully marked as completed.")
                        else:
                            # State assign fallback
                            db_status_val = status_map_to_db.get(new_status, 'pending')
                            bk.status = db_status_val
                            bk.save()
                            messages.success(request, f"Proposal updated to: {new_status}!")
                    else:
                        messages.error(request, "Permission denied on this booking record.")
                except Exception as e:
                    messages.error(request, f"Update failed: {str(e)}")
            else:
                messages.error(request, "Database Error: The BookingRequest model is missing from system.")
                
            return redirect('my_bookings')

        # ─── CASE C: RATE SERVICE PROVIDER ───
        elif action == 'rate':
            booking_id = request.POST.get('booking_id')
            comment = request.POST.get('comment', '').strip()
            
            # Fetch the rating uniquely named key or fallback to global rating key
            rating_str = request.POST.get(f'rating_{booking_id}') or request.POST.get('rating')
            
            # Debug POST logging
            import os
            try:
                debug_p = os.path.join(os.path.dirname(__file__), 'debug_post_rate.txt')
                with open(debug_p, 'w') as f_dbg:
                    f_dbg.write(f"POST params: {dict(request.POST)}\n")
            except Exception as e_dbg:
                print(f"DEBUG: Error logging POST: {e_dbg}")
            
            Review = models.get('Review')
            if BookingRequest and Review:
                try:
                    bk = BookingRequest.objects.get(id=booking_id)
                    
                    if bk.client != request.user:
                        messages.error(request, "Permission denied: Only the client who placed this booking can write a review.")
                        return redirect('my_bookings')
                        
                    if hasattr(bk, 'review') and bk.review:
                        messages.error(request, "You have already rated this booking.")
                        return redirect('my_bookings')
                    
                    # Robust digit-extraction parsing of rating score to prevent formatting issues
                    import re
                    score = 5
                    if rating_str:
                        match = re.search(r'\d+', str(rating_str))
                        if match:
                            try:
                                score = int(match.group())
                            except Exception:
                                score = 5

                    if score < 1 or score > 5:
                        score = 5

                    try:
                        Review.objects.create(
                            booking=bk,
                            reviewer=request.user,
                            reviewee=bk.worker.user,
                            rating=score,
                            comment=comment
                        )
                        messages.success(request, f"Feedback submitted successfully! You rated {bk.worker.user.name or 'Specialist'} with {score} Stars.")
                    except ValueError as ve:
                        err_msg = str(ve)
                        if "7 days" in err_msg.lower():
                            messages.error(request, "Rating Error: Your client account must be at least 7 days old to leave a rating feedback.")
                        else:
                            messages.error(request, f"Validation Constraint: {err_msg}")
                except Exception as e:
                    messages.error(request, f"Error submitting review: {str(e)}")
            else:
                messages.error(request, "Database Error: Review models not found.")
            return redirect('my_bookings')

    # Auto-ensure WorkerProfile for logged-in user if they are flagged as a worker in custom User
    if request.user.is_authenticated and WorkerProfile:
        try:
            if getattr(request.user, 'is_worker', False):
                WorkerProfile.objects.get_or_create(user=request.user)
        except Exception as e:
            print(f"DEBUG: Error establishing worker profile: {e}")

    # Load All Sent / Received Bookings for Context Renders
    my_sent_bookings = []
    my_received_bookings = []

    # Dump database reviews for debug analysis
    try:
        Review_dbg = get_app_models().get('Review')
        if Review_dbg:
            import os
            dbg_p = os.path.join(os.path.dirname(__file__), 'debug_reviews_my_bookings.txt')
            with open(dbg_p, 'w') as f:
                f.write(f"My bookings review dump: {Review_dbg.objects.count()}\n")
                for r in Review_dbg.objects.all():
                    f.write(f"ID: {r.id} | rating={r.rating} type={type(r.rating)} | comment={r.comment}\n")
    except Exception as d_err:
        print(f"DEBUG Error dumping Reviews: {d_err}")

    if BookingRequest:
        try:
            # Print database summary in server log for verification
            all_bookings_count = BookingRequest.objects.count()
            print(f"DEBUG: Total BookingRequests in DB: {all_bookings_count}")
            
            # Outgoing client request proposals
            db_sent = BookingRequest.objects.filter(client=request.user).select_related('worker__user', 'review').prefetch_related('worker__categories')
            for b in db_sent:
                worker_name = "Specialist"
                worker_category = "General"
                worker_phone = "0321-7654321"
                
                if b.worker and b.worker.user:
                    w_user = b.worker.user
                    worker_name = getattr(w_user, 'name', '') or getattr(w_user, 'username', '') or w_user.email
                    worker_phone = getattr(w_user, 'phone', '') or '0321-7654321'
                    categories_list = list(b.worker.categories.all())
                    worker_category = categories_list[0].name if categories_list else "Specialist"
                    
                status_raw = str(b.status).lower().strip() if b.status else 'pending'
                ui_status = status_map_to_ui.get(status_raw, 'Pending')

                review_data = None
                try:
                    if hasattr(b, 'review') and b.review:
                        review_data = {
                            'rating': int(b.review.rating) if b.review.rating is not None else 5,
                            'comment': b.review.comment,
                        }
                except Exception:
                    pass
                
                my_sent_bookings.append({
                    'id': b.id,
                    'worker_name': worker_name,
                    'worker_category': worker_category,
                    'worker_phone': worker_phone,
                    'notes': b.description or 'No details specified',
                    'status': ui_status,
                    'review': review_data,
                })
                
            # Incoming worker received proposals
            db_received = BookingRequest.objects.filter(worker__user=request.user).exclude(status__in=['rejected', 'completed']).select_related('client', 'review')
            for b in db_received:
                client_name = "Client"
                client_phone = "0300-1234567"
                client_email = "client@workverse.pk"
                
                if b.client:
                    client_name = getattr(b.client, 'name', '') or getattr(b.client, 'username', '') or b.client.email
                    client_phone = getattr(b.client, 'phone', '') or '0300-1234567'
                    client_email = b.client.email
                    
                status_raw = str(b.status).lower().strip() if b.status else 'pending'
                ui_status = status_map_to_ui.get(status_raw, 'Pending')

                review_data = None
                try:
                    if hasattr(b, 'review') and b.review:
                        review_data = {
                            'rating': int(b.review.rating) if b.review.rating is not None else 5,
                            'comment': b.review.comment,
                        }
                except Exception:
                    pass
                
                my_received_bookings.append({
                    'id': b.id,
                    'client_name': client_name,
                    'client_phone': client_phone,
                    'client_email': client_email,
                    'notes': b.description or 'No details specified',
                    'status': ui_status,
                    'review': review_data,
                })
        except Exception as e:
            print(f"DEBUG: Exception in my_bookings query: {e}")

    # Determine if worker role should be active in workspace context
    is_worker_ctx = False
    if request.user.is_authenticated:
        has_profile = False
        if WorkerProfile:
            try:
                has_profile = WorkerProfile.objects.filter(user=request.user).exists()
            except Exception:
                pass
        is_worker_ctx = getattr(request.user, 'is_worker', False) or has_profile or len(my_received_bookings) > 0

    pending_bookings_count = sum(1 for b in my_received_bookings if b['status'].lower() == 'pending')
    pending_sent_bookings_count = sum(1 for b in my_sent_bookings if b['status'].lower() != 'completed')

    # Mark as viewed
    request.session['bookings_viewed'] = True
    request.session['last_seen_pending_count'] = pending_bookings_count
    request.session['last_seen_sent_count'] = pending_sent_bookings_count

    return render(request, 'my_bookings.html', {
        'sent_bookings': my_sent_bookings,
        'received_bookings': my_received_bookings,
        'is_worker': is_worker_ctx,
        'pending_bookings_count': pending_bookings_count,
        'pending_sent_bookings_count': pending_sent_bookings_count,
    })

def contact(request):
    """Platform Contact View"""
    return render(request, 'base.html')

def login_view(request):
    """User Sign In View (Unified Full-Viewport Layout)"""
    if request.user.is_authenticated:
        return redirect('find_workers')  # If already logged in, redirect home
        
    next_url = request.GET.get('next') or request.POST.get('next') or 'find_workers'

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            
            user = authenticate(request, username=email, password=password)
            if user is None:
                # Fallback, some setups use standard authenticate(request, email=email, ...)
                user = authenticate(request, email=email, password=password)
                
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {getattr(user, 'name', email)}!")
                return redirect(next_url)
            else:
                messages.error(request, "Invalid email or password.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = LoginForm()
        
    return render(request, 'login.html', {'form': form})

def signup_view(request):
    """User Registration View (Unified Full-Viewport Layout)"""
    if request.user.is_authenticated:
        return redirect('find_workers')  # If already logged in, redirect home
        
    next_url = request.GET.get('next') or request.POST.get('next') or 'find_workers'

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            email = form.cleaned_data.get('email')
            phone = form.cleaned_data.get('phone')
            password = form.cleaned_data.get('password')
            
            try:
                # Create the custom user
                new_user = User.objects.create_user(
                    email=email.lower().strip(),
                    phone=phone.strip(),
                    name=name.strip(),
                    password=password
                )
                
                # Standard login post-creation
                authenticated_user = authenticate(request, username=email, password=password)
                if authenticated_user is None:
                    authenticated_user = authenticate(request, email=email, password=password)
                    
                if authenticated_user is not None:
                    login(request, authenticated_user)
                    messages.success(request, f"Account created! Welcome, {name}.")
                    return redirect(next_url)
                else:
                    messages.success(request, "Signup complete! Please login.")
                    return redirect('login')
            except Exception as e:
                messages.error(request, f"Error saving details: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').capitalize()}: {error}")
    else:
        form = SignupForm()
        
    return render(request, 'signup.html', {'form': form})

def logout_view(request):
    """User Sign Out Helper"""
    logout(request)
    messages.success(request, "Successfully logged out.")
    return redirect('find_workers')

def become_worker(request):
    """Become a Freelance Specialist onboarding page (Unified Full-Viewport Layout)"""
    if not request.user.is_authenticated:
        return render(request, 'become_worker.html', {'is_unauthenticated': True})

    models = get_app_models()
    WorkerProfile = models['WorkerProfile']
    City = models['City']
    Category = models['Category']

    if request.method == 'POST':
        form = BecomeWorkerForm(request.POST)
        if form.is_valid():
            category_name = form.cleaned_data.get('category')
            city_name = form.cleaned_data.get('city')
            experience = form.cleaned_data.get('experience')
            bio = form.cleaned_data.get('bio')
            
            # Upgrade current user to worker status
            user = request.user
            user.is_worker = True
            
            if hasattr(user, 'category'):
                user.category = category_name
            if hasattr(user, 'city'):
                user.city = city_name
            if hasattr(user, 'experience'):
                user.experience = experience
            if hasattr(user, 'bio'):
                user.bio = bio
            
            try:
                user.save()
            except Exception:
                pass
            
            # Save technical details directly to WorkerProfile database schema
            if WorkerProfile:
                try:
                    profile, created = WorkerProfile.objects.get_or_create(user=user)
                    profile.bio = bio
                    profile.experience_years = parse_experience_years(experience)
                    profile.is_available = True
                    
                    if City and city_name:
                        city_obj, _ = City.objects.get_or_create(name=city_name)
                        profile.city = city_obj
                        
                    profile.save()
                    
                    if Category and category_name:
                        category_obj, _ = Category.objects.get_or_create(
                            name=category_name, 
                            defaults={'slug': category_name.lower().replace(' ', '-')}
                        )
                        profile.categories.add(category_obj)
                except Exception as e:
                    messages.error(request, f"Error completing worker profile: {str(e)}")
                    return redirect('become_worker')
            
            messages.success(request, f"Congratulations, {getattr(user, 'name', 'Specialist')}! You are now registered as a local {category_name} in {city_name}.")
            return redirect('find_workers')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').capitalize()}: {error}")
    else:
        form = BecomeWorkerForm()
        
    return render(request, 'become_worker.html', {
        'form': form,
        'is_unauthenticated': False
    })

def worker_dashboard(request):
    """Worker incoming bookings and metrics dashboard"""
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to view the worker dashboard.")
        return redirect('login')
        
    models = get_app_models()
    WorkerProfile = models['WorkerProfile']
    BookingRequest = models['BookingRequest']
    Review = models['Review']
    
    profile = None
    if WorkerProfile:
        try:
            profile, created = WorkerProfile.objects.get_or_create(user=request.user)
        except Exception:
            pass
            
    if not profile or not getattr(request.user, 'is_worker', False):
        messages.warning(request, "You are not registered as a specialist. Get started by completing onboarding below.")
        return redirect('become_worker')
        
    status_map_to_db = {
        'Pending': 'pending',
        'Accepted': 'accepted',
        'Declined': 'rejected',
        'Completed': 'completed',
    }
    status_map_to_ui = {
        'pending': 'Pending',
        'accepted': 'Accepted',
        'rejected': 'Declined',
        'completed': 'Completed',
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_availability':
            profile.is_available = not profile.is_available
            profile.save()
            status_text = "Available" if profile.is_available else "Busy"
            messages.success(request, f"Your status has been updated to '{status_text}'.")
            return redirect('worker_dashboard')
            
        elif action == 'respond':
            booking_id = request.POST.get('booking_id')
            new_status = request.POST.get('status') # 'Accepted', 'Declined', 'Completed'
            if BookingRequest:
                try:
                    bk = BookingRequest.objects.get(id=booking_id)
                    if bk.worker and bk.worker.user == request.user:
                        if new_status == 'Accepted' and hasattr(bk, 'accept'):
                            bk.accept()
                            messages.success(request, "Proposal successfully accepted! Callback initiated.")
                        elif new_status == 'Declined' and hasattr(bk, 'reject'):
                            bk.reject()
                            messages.success(request, "Proposal successfully declined.")
                        elif new_status == 'Completed' and hasattr(bk, 'mark_complete'):
                            bk.mark_complete()
                            messages.success(request, "Task successfully marked as completed.")
                        else:
                            db_status = status_map_to_db.get(new_status, 'pending')
                            bk.status = db_status
                            bk.save()
                            messages.success(request, f"Proposal updated to: {new_status}!")
                    else:
                        messages.error(request, "Permission denied.")
                except Exception as e:
                    messages.error(request, f"Action failed: {str(e)}")
            return redirect('worker_dashboard')
            
    # Calculate statistics
    total_proposals = 0
    pending_proposals = 0
    active_proposals = 0
    completed_proposals = 0
    avg_rating = 0.0
    reviews_count = 0
    
    my_proposals = []
    recent_reviews = []
    
    if BookingRequest:
        try:
            total_proposals = BookingRequest.objects.filter(worker=profile).count()
            pending_proposals = BookingRequest.objects.filter(worker=profile, status='pending').count()
            active_proposals = BookingRequest.objects.filter(worker=profile, status='accepted').count()
            completed_proposals = BookingRequest.objects.filter(worker=profile, status='completed').count()
            
            db_received = BookingRequest.objects.filter(worker=profile).select_related('client', 'review').order_by('-id')
            for b in db_received:
                client_name = "Client"
                client_phone = "0300-1234567"
                client_email = "client@workverse.pk"
                if b.client:
                    client_name = getattr(b.client, 'name', '') or getattr(b.client, 'username', '') or b.client.email
                    client_phone = getattr(b.client, 'phone', '') or '0300-1234567'
                    client_email = b.client.email
                    
                status_raw = str(b.status).lower().strip() if b.status else 'pending'
                ui_status = status_map_to_ui.get(status_raw, 'Pending')
                
                review_data = None
                try:
                    if hasattr(b, 'review') and b.review:
                        review_data = {
                            'rating': int(b.review.rating) if b.review.rating is not None else 5,
                            'comment': b.review.comment,
                        }
                except Exception:
                    pass
                my_proposals.append({
                    'id': b.id,
                    'client_name': client_name,
                    'client_phone': client_phone,
                    'client_email': client_email,
                    'notes': b.description or 'No details specified',
                    'status': ui_status,
                    'review': review_data,
                })
        except Exception as e:
            print(f"DEBUG Error in dashboard booking queries: {e}")
            
    if Review:
        try:
            db_reviews = Review.objects.filter(reviewee=request.user).select_related('reviewer').order_by('-created_at')
            
            # Temporary debug log to inspect real ratings
            import os
            try:
                debug_path = os.path.join(os.path.dirname(__file__), 'debug_reviews.txt')
                with open(debug_path, 'w') as dbg_f:
                    dbg_f.write(f"Reviews Total: {db_reviews.count()}\n")
                    for r in db_reviews:
                        dbg_f.write(f"Review ID: {r.id if hasattr(r, 'id') else 'no_id'} - Rating: {r.rating} ({type(r.rating)}) - Comment: {r.comment}\n")
            except Exception as dbg_err:
                print(f"DEBUG Error writing debug file: {dbg_err}")

            reviews_count = db_reviews.count()
            if reviews_count > 0:
                avg_rating = round(sum(r.rating for r in db_reviews) / reviews_count, 1)
            else:
                avg_rating = 0.0
                
            for r in db_reviews[:5]:
                rev_name = getattr(r.reviewer, 'name', '') or r.reviewer.email
                r_rating = int(r.rating) if r.rating is not None else 5
                recent_reviews.append({
                    'reviewer_name': rev_name,
                    'rating': r_rating,
                    'stars_filled': '★' * r_rating,
                    'stars_empty': '★' * (5 - r_rating),
                    'comment': r.comment,
                    'created_at': r.created_at if hasattr(r, 'created_at') else None
                })
        except Exception as e:
            print(f"DEBUG Error in dashboard review queries: {e}")
            
    # Category list and city
    p_categories = list(profile.categories.all()) if profile else []
    category_name = p_categories[0].name if p_categories else 'General Specialist'
    city_name = profile.city.name if profile and profile.city else 'Select City'
    
    pending_bookings_count, pending_sent_count = get_user_booking_counts(request)
    
    return render(request, 'worker_dashboard.html', {
        'profile': profile,
        'category_name': category_name,
        'city_name': city_name,
        'total_proposals': total_proposals,
        'pending_proposals': pending_proposals,
        'active_proposals': active_proposals,
        'completed_proposals': completed_proposals,
        'avg_rating': avg_rating,
        'reviews_count': reviews_count,
        'my_proposals': my_proposals,
        'recent_reviews': recent_reviews,
        'pending_bookings_count': pending_bookings_count,
        'is_worker': True,
    })

def worker_profile_edit(request):
    """Worker settings and specifications editor"""
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to edit your profile.")
        return redirect('login')
        
    models = get_app_models()
    WorkerProfile = models['WorkerProfile']
    City = models['City']
    Category = models['Category']
    
    if not WorkerProfile:
        messages.error(request, "Worker Profile database component is offline.")
        return redirect('find_workers')
        
    try:
        profile, created = WorkerProfile.objects.get_or_create(user=request.user)
    except Exception as e:
        messages.error(request, f"Error locating/creating worker profile: {str(e)}")
        return redirect('find_workers')
        
    if not getattr(request.user, 'is_worker', False):
        messages.warning(request, "You are not registered as a specialist. Get started by completing onboarding below.")
        return redirect('become_worker')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_availability':
            is_available_raw = request.POST.get('is_available')
            profile.is_available = True if is_available_raw in ['true', 'on', '1', 'True'] else False
            profile.save()
            return JsonResponse({'status': 'success', 'is_available': profile.is_available})
            
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        category_name = request.POST.get('category', '').strip()
        city_name = request.POST.get('city', '').strip()
        experience = request.POST.get('experience', '').strip()
        bio = request.POST.get('bio', '').strip()
        is_available_raw = request.POST.get('is_available')
        
        if not name:
            messages.error(request, "Full Name is required.")
        else:
            try:
                user = request.user
                user.name = name
                if phone:
                    user.phone = phone
                user.save()
                
                profile.bio = bio
                profile.experience_years = parse_experience_years(experience)
                profile.is_available = True if is_available_raw in ['true', 'on', '1', 'True'] else False
                
                if City and city_name:
                    city_obj, _ = City.objects.get_or_create(name=city_name)
                    profile.city = city_obj
                    
                profile.save()
                
                if Category and category_name:
                    category_obj, _ = Category.objects.get_or_create(
                        name=category_name, 
                        defaults={'slug': category_name.lower().replace(' ', '-')}
                    )
                    profile.categories.clear()
                    profile.categories.add(category_obj)
                    
                messages.success(request, "Your professional profile was successfully updated!")
                return redirect('worker_profile_edit')
            except Exception as e:
                messages.error(request, f"Error updating profile: {str(e)}")
                
    p_categories = list(profile.categories.all()) if profile else []
    current_category = p_categories[0].name if p_categories else ''
    current_city = profile.city.name if profile and profile.city else ''
    
    categories_choices = []
    if Category:
        categories_choices = [cat.name for cat in Category.objects.all()]
    if not categories_choices:
        categories_choices = ['Plumber', 'Electrician', 'Painter', 'Mechanic', 'Labour', 'Carpenter', 'Other']
    
    # Sort with 'Other' at the end
    cats_non_other = [c for c in categories_choices if c.lower() != 'other']
    cats_other = [c for c in categories_choices if c.lower() == 'other']
    categories_choices = cats_non_other + cats_other
        
    cities_choices = []
    if City:
        cities_choices = [city.name for city in City.objects.all()]
    if not cities_choices:
        cities_choices = ['Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Other']

    # Sort with 'Other' at the end
    cities_non_other = [c for c in cities_choices if c.lower() != 'other']
    cities_other = [c for c in cities_choices if c.lower() == 'other']
    cities_choices = cities_non_other + cities_other
        
    experience_choices = [
        ('1 year', '1 Year Experience', 1),
        ('2 years', '2 Years Experience', 2),
        ('3 years', '3 Years Experience', 3),
        ('5 years', '5 Years Experience', 5),
        ('7 years', '7 Years Experience', 7),
        ('10 years', '10 Years Experience', 10),
        ('15+ years', '15+ Years Experience', 15),
    ]
    
    current_exp_years = profile.experience_years
    pending_bookings_count, pending_sent_count = get_user_booking_counts(request)
    
    return render(request, 'worker_profile_edit.html', {
        'profile': profile,
        'current_category': current_category,
        'current_city': current_city,
        'categories_choices': categories_choices,
        'cities_choices': cities_choices,
        'experience_choices': experience_choices,
        'current_exp_years': current_exp_years,
        'pending_bookings_count': pending_bookings_count,
        'pending_sent_bookings_count': pending_sent_count,
    })

def admin_overview(request):
    """Platform analytical health checks"""
    return render(request, 'base.html')

def admin_users(request):
    """Platform database manager for system accounts"""
    return render(request, 'base.html')

def admin_workers(request):
    """Platform database manager for worker credentials"""
    return render(request, 'base.html')

def admin_bookings(request):
    """View and auditing panel for all system receipts"""
    return render(request, 'base.html')

def worker_detail(request, worker_id):
    """Worker public profile page with bio, feedback reviews and interactive hiring proposal dispatch"""
    models = get_app_models()
    WorkerProfile = models['WorkerProfile']
    Review = models['Review']
    BookingRequest = models['BookingRequest']
    
    worker_p = None
    if WorkerProfile:
        try:
            worker_p = WorkerProfile.objects.select_related('user', 'city').prefetch_related('categories').get(id=worker_id)
        except Exception:
            try:
                worker_p = WorkerProfile.objects.select_related('user', 'city').prefetch_related('categories').get(user_id=worker_id)
            except Exception:
                pass
                
    if not worker_p:
        messages.error(request, "Specialist Profile not found or has been deactivated.")
        return redirect('find_workers')
        
    u = worker_p.user
    name = getattr(u, 'name', '') or getattr(u, 'username', '') or u.email
    initials = ''.join([part[0].upper() for part in name.split()[:2]]) if len(name.split()) >= 2 else name[:2].upper()
    if not initials:
        initials = 'SP'
        
    p_categories = list(worker_p.categories.all())
    category_name = p_categories[0].name if p_categories else 'Other'
    city_name = worker_p.city.name if worker_p.city else 'Other'
    status_str = 'Busy' if not worker_p.is_available else 'Available'
    
    avg_rating = 0.0
    if Review:
        try:
            reviews_list_rating = Review.objects.filter(reviewee=worker_p.user)
            reviews_count = reviews_list_rating.count()
            if reviews_count > 0:
                avg_rating = round(sum(r.rating for r in reviews_list_rating) / reviews_count, 1)
        except Exception:
            pass
        
    worker_data = {
        'id': str(worker_p.id),
        'name': name,
        'initials': initials,
        'category': category_name,
        'city': city_name,
        'rating': str(avg_rating),
        'is_verified': worker_p.is_verified,
        'bio': worker_p.bio or "Specialized domestic technician. Friendly service and professional results guaranteed.",
        'experience': f"{worker_p.experience_years} year" if worker_p.experience_years == 1 else f"{worker_p.experience_years} years",
        'status': status_str,
        'phone': getattr(u, 'phone', '0300-1234567'),
        'is_current_user': request.user.is_authenticated and (str(u.id) == str(request.user.id))
    }
    
    # Process instant callback list creation posting
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Authentication required: Please log in to request a callback session.")
            return redirect('login')
            
        # SECURITY SECURE RULE: Specialist cannot book themselves
        if request.user == worker_p.user:
            messages.error(request, "Security lock: You cannot send a booking proposal to your own account.")
            return redirect('worker_detail', worker_id=str(worker_p.id))
            
        notes = request.POST.get('notes', '')
        if BookingRequest:
            try:
                BookingRequest.objects.create(
                    client=request.user,
                    worker=worker_p,
                    description=notes,
                    status='pending'
                )
                messages.success(request, f"Your service proposal was successfully sent to {name}!")
            except Exception as e:
                messages.error(request, f"Error saving booking request: {str(e)}")
        else:
            messages.error(request, "Database Error: The BookingRequest model was not detected.")
            
        return redirect('my_bookings')
        
    # Retrieve reviews list
    reviews_list = []
    if Review:
        try:
            reviews_list = Review.objects.filter(reviewee=worker_p.user).select_related('reviewer').order_by('-created_at')
        except Exception:
            try:
                reviews_list = Review.objects.filter(reviewee=worker_p.user).select_related('reviewer')
            except Exception:
                pass
                
    reviews_data_rendered = []
    for r in reviews_list:
        rev_name = getattr(r.reviewer, 'name', '') or r.reviewer.email
        r_rating = int(r.rating) if r.rating is not None else 5
        reviews_data_rendered.append({
            'reviewer_name': rev_name,
            'rating': r_rating,
            'stars_filled': '★' * r_rating,
            'stars_empty': '★' * (5 - r_rating),
            'comment': r.comment,
            'created_at': r.created_at if hasattr(r, 'created_at') else None
        })
        
    pending_bookings_count, pending_sent_count = get_user_booking_counts(request)
                
    is_worker_ctx = False
    if request.user.is_authenticated:
        has_profile = False
        if WorkerProfile:
            try:
                has_profile = WorkerProfile.objects.filter(user=request.user).exists()
            except Exception:
                pass
        is_worker_ctx = getattr(request.user, 'is_worker', False) or has_profile
        
    return render(request, 'worker_detail.html', {
        'worker': worker_data,
        'reviews': reviews_data_rendered,
        'reviews_count': len(reviews_data_rendered),
        'pending_bookings_count': pending_bookings_count,
        'is_worker': is_worker_ctx
    })
