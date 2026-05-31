from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class UserManager(BaseUserManager):

    def create_user(self, email, phone, name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not phone:
            raise ValueError("Phone number is required")
        email = self.normalize_email(email)
        user = self.model(email=email, phone=phone, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, phone, name, password, **extra_fields)


class City(models.Model):
    name      = models.CharField(max_length=100, unique=True)
    province  = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Cities"
        ordering = ["name"]

    def __str__(self):
        return self.name

class Category(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    slug        = models.SlugField(max_length=100, unique=True)
    icon        = models.CharField(max_length=50, blank=True, help_text="Tabler icon name e.g. ti-droplet")
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

class User(AbstractBaseUser, PermissionsMixin):
    name       = models.CharField(max_length=150) 
    email      = models.EmailField(unique=True)
    phone      = models.CharField(max_length=15, unique=True)  # unique to prevent fake accounts
    profile_picture = models.ImageField(upload_to="profile_pics/", null=True, blank=True)
    is_worker  = models.BooleanField(default=False)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False) 
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["phone", "name"]

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.name} ({self.email})"

    @property
    def is_eligible_to_rate(self):
        return (timezone.now() - self.date_joined).days >= 7

class WorkerProfile(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name="worker_profile")
    categories  = models.ManyToManyField(Category, through="WorkerCategory", related_name="workers")
    city        = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, related_name="workers")
    bio         = models.TextField(blank=True, help_text="Short description of experience and services")
    experience_years = models.PositiveIntegerField(default=0)

    is_available     = models.BooleanField(default=True, help_text="Toggle off when busy today")
    unavailable_until = models.DateField(
        null=True, blank=True,
        help_text="Set a future date if taking extended leave"
    )
    is_verified      = models.BooleanField(default=False)
    verified_at      = models.DateTimeField(null=True, blank=True)
    total_jobs_completed = models.PositiveIntegerField(default=0)
    average_rating       = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name} — Worker Profile"

    def check_and_award_verified(self):
        if not self.is_verified and self.total_jobs_completed >= 15:
            self.is_verified = True
            self.verified_at = timezone.now()
            self.save()

    def update_average_rating(self):
        reviews = self.user.received_reviews.all()
        if reviews.exists():
            total = sum(r.rating for r in reviews)
            self.average_rating = round(total / reviews.count(), 2)
            self.save()

class WorkerCategory(models.Model):
    worker   = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("worker", "category")
        verbose_name_plural = "Worker Categories"

    def __str__(self):
        return f"{self.worker.user.name} → {self.category.name}"


class BookingRequest(models.Model):

    class Status(models.TextChoices):
        PENDING   = "pending",   "Pending"
        ACCEPTED  = "accepted",  "Accepted"
        REJECTED  = "rejected",  "Rejected"
        COMPLETED = "completed", "Completed"

    client      = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="sent_bookings",
        help_text="The user who sent the request"
    )
    worker      = models.ForeignKey(
        WorkerProfile, on_delete=models.CASCADE,
        related_name="received_bookings"
    )
    description = models.TextField(help_text="Client describes the job in detail")
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at   = models.DateTimeField(auto_now_add=True)
    accepted_at  = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    auto_complete_after = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client.name} → {self.worker.user.name} [{self.status}]"

    def save(self, *args, **kwargs):
        # Block worker from booking himself
        if self.client == self.worker.user:
            raise ValueError("A worker cannot send a booking request to themselves.")
        super().save(*args, **kwargs)

    def accept(self):
        self.status = self.Status.ACCEPTED
        self.accepted_at = timezone.now()
        # Auto-complete 7 days after acceptance if client doesn't confirm
        self.auto_complete_after = timezone.now() + timezone.timedelta(days=7)
        self.save()

    def reject(self):
        self.status = self.Status.REJECTED
        self.save()

    def mark_complete(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save()
        profile = self.worker
        profile.total_jobs_completed += 1
        profile.save()
        profile.check_and_award_verified()

    @property
    def can_be_rated(self):
        """Review only allowed after completion."""
        return self.status == self.Status.COMPLETED

    @property
    def is_overdue_for_auto_complete(self):
        if self.auto_complete_after and self.status == self.Status.ACCEPTED:
            return timezone.now() >= self.auto_complete_after
        return False

class Review(models.Model):
    booking   = models.OneToOneField(
        BookingRequest, on_delete=models.CASCADE,
        related_name="review"
    )
    reviewer  = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="given_reviews"
    )
    reviewee  = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="received_reviews"
    )
    rating    = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment   = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reviewer.name} → {self.reviewee.name} ({self.rating}★)"

    def save(self, *args, **kwargs):
        if not self.booking.can_be_rated:
            raise ValueError("Cannot review a booking that is not completed.")
        if self.reviewer != self.booking.client:
            raise ValueError("Only the client of a booking can leave a review.")
        if not self.reviewer.is_eligible_to_rate:
            raise ValueError("Account must be at least 7 days old to leave a review.")
        super().save(*args, **kwargs)
        self.booking.worker.update_average_rating()

class ContactMessage(models.Model):

    class IssueType(models.TextChoices):
        GENERAL         = "general",         "General Inquiry"
        WORKER_COMPLAINT = "worker_complaint", "Complaint Against Worker"
        USER_COMPLAINT  = "user_complaint",  "Complaint Against User"
        TECHNICAL       = "technical",       "Technical Issue"
        OTHER           = "other",           "Other"

    user       = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="contact_messages"
    )
    name       = models.CharField(max_length=150)
    email      = models.EmailField()
    phone      = models.CharField(max_length=15, blank=True)
    issue_type = models.CharField(max_length=30, choices=IssueType.choices, default=IssueType.GENERAL)
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.issue_type} ({self.created_at.date()})"