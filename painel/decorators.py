from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render


def staff_necessario(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not request.user.is_staff:
            return render(request, "403.html", status=403)
        return view_func(request, *args, **kwargs)

    return wrapper
