# Users

There are two ways to add users to your Django application: manually via the admin interface, or by enabling public self-registration.

## Option 1: Add Users via the Django Admin

1. Log in to the Django admin panel at `/admin/` using a superuser account.
2. Navigate to **Authentication and Authorization → Users**.
3. Click **Add User** in the top-right corner.
4. Enter a username and password, then click **Save**.
5. On the following screen, fill in any additional profile details (email, first/last name, permissions) and click **Save** again.

???+ Tip
    To create a superuser from the command line, run:
    ```bash
    python manage.py createsuperuser
    ```

---

## Option 2: Enable User Self-Registration

To allow users to register themselves, you can enable signups via an environment variable or directly in Django settings.

### Via `.env.prod`

Add the following line to your `.env.prod` file:

```env
DJANGO_ENABLE_SIGNUPS=true
```

### Via Django Settings

Alternatively, set the flag directly in your `settings.py`:

```python
ENABLE_SIGNUPS = True
```

Once enabled, a registration page will be available for new users to sign up without admin intervention.

???+ Info
    Signups will require an email server to be configured, otherwise users won't be able to verify their email. In case your admin account
    doesn't have an email configured, add one first.