
import os
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "supermarket.settings"
)

django.setup()

from django.contrib.auth import get_user_model

username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

if username and password:
    User = get_user_model()
    user = User.objects.filter(username=username).first()

    if user is None:
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        print("Demo superuser created successfully.")
    elif not user.is_superuser:
        raise RuntimeError(
            "Existing user is not a superuser."
        )
    else:
        print("Demo superuser already exists.")
else:
    print("No demo superuser configuration provided.")
