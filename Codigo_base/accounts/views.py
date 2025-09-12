from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .forms import SignUpForm
from django.contrib import messages

# Create your views here.

# Sign Up
def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Usuario registrado correctamente. Ahora puedes iniciar sesión.")
            return redirect("login")  # Redirigir a la página de login
        else:
            messages.error(request, "Hubo un error en el registro. Por favor revisa los datos.")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})



# Login
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("/")
    else:
        form = AuthenticationForm()
    return render(request, "accounts/login.html", {"form":form})

# Logout
def logout_view(request):
    logout(request)
    return redirect("/")


