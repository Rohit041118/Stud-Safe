from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse
from django.db.models import Q, Count
from .models import Note, Subject, Bookmark
from .forms import SignUpForm, NoteUploadForm


def home(request):
    """Landing page with hero, features, and recent notes."""
    recent_notes = Note.objects.select_related('subject', 'uploaded_by')[:6]
    subjects = Subject.objects.annotate(note_count=Count('notes'))
    total_notes = Note.objects.count()
    total_subjects = Subject.objects.count()
    context = {
        'recent_notes': recent_notes,
        'subjects': subjects,
        'total_notes': total_notes,
        'total_subjects': total_subjects,
    }
    return render(request, 'home.html', context)


def signup_view(request):
    """User registration page."""
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Stud Safe, {user.first_name}! 🎉')
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    """User login page."""
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}! 👋')
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def logout_view(request):
    """Log out the user."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


def browse_notes(request):
    """Browse and search notes, optionally filtered by subject."""
    notes = Note.objects.select_related('subject', 'uploaded_by')
    subjects = Subject.objects.annotate(note_count=Count('notes'))

    # Filter by subject
    subject_id = request.GET.get('subject')
    if subject_id:
        notes = notes.filter(subject_id=subject_id)

    # Search
    query = request.GET.get('q', '')
    if query:
        notes = notes.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(subject__name__icontains=query)
        )

    context = {
        'notes': notes,
        'subjects': subjects,
        'current_subject': subject_id,
        'search_query': query,
    }
    return render(request, 'browse.html', context)


@login_required(login_url='login')
def upload_note(request):
    """Upload a new note."""
    if request.method == 'POST':
        form = NoteUploadForm(request.POST, request.FILES)
        if form.is_valid():
            note = form.save(commit=False)
            note.uploaded_by = request.user
            note.save()
            messages.success(request, 'Your notes have been uploaded successfully! 📚')
            return redirect('browse')
    else:
        form = NoteUploadForm()
    return render(request, 'upload.html', {'form': form})


@login_required(login_url='login')
def download_note(request, note_id):
    """Download a note file and increment download count."""
    note = get_object_or_404(Note, id=note_id)
    note.downloads += 1
    note.save(update_fields=['downloads'])
    return FileResponse(note.file.open('rb'), as_attachment=True, filename=note.file.name.split('/')[-1])


@login_required(login_url='login')
def dashboard(request):
    """User dashboard showing their uploaded notes and bookmarks."""
    user_notes = Note.objects.filter(uploaded_by=request.user).select_related('subject')
    user_bookmarks = Bookmark.objects.filter(user=request.user).select_related('note', 'note__subject', 'note__uploaded_by')
    context = {
        'user_notes': user_notes,
        'user_bookmarks': user_bookmarks,
    }
    return render(request, 'dashboard.html', context)


@login_required(login_url='login')
def toggle_bookmark(request, note_id):
    """Toggle bookmark on a note."""
    note = get_object_or_404(Note, id=note_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, note=note)
    if not created:
        bookmark.delete()
        messages.info(request, 'Bookmark removed.')
    else:
        messages.success(request, 'Note bookmarked! 🔖')
    return redirect(request.META.get('HTTP_REFERER', 'browse'))