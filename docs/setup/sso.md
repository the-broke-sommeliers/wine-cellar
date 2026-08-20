# SSO

Django supports Single Sign-On via OpenID Connect through [django-allauth](https://docs.allauth.org/). Once configured, users can log in with any compatible identity provider (e.g. Google, Microsoft Entra, Okta, Keycloak).

## Configuring a Provider via the Django Admin

OIDC providers can be added and managed at runtime through the Django admin.

1. Log in to the admin panel at `/admin/`.
2. Navigate to **Social Accounts → Social applications**.
3. Click **Add Social Application** and fill in the following fields:

| Field | Value |
|---|---|
| **Provider** | `OpenID Connect` |
| **Provider ID** | A unique slug for this provider, e.g. `my-okta` |
| **Name** | A display name, e.g. `Okta` |
| **Client ID** | Your OIDC client ID from the identity provider |
| **Secret key** | Your OIDC client secret |
| **Key** | Leave blank (not used for OIDC) |
| **Settings** | See below |

4. In the **Settings** field, enter a JSON object with at least the `server_url` of your identity provider:

```json
{
  "server_url": "https://your-idp.example.com"
}
```

allauth will automatically discover the provider's endpoints via the `/.well-known/openid-configuration` URL.

5. Assign the application to the appropriate **Sites** and click **Save**.

!!! Note

    If login is blocked by the app's Content Security Policy (the browser console shows a `form-action` violation), add your identity provider's domain to `DJANGO_CSP_FORM_ACTION_EXTRA` (space-separated if you have more than one provider), e.g.:

    ```
    DJANGO_CSP_FORM_ACTION_EXTRA=https://your-idp.example.com
    ```

## Callback URL

When registering the application with your identity provider, set the callback (redirect) URL to:

```
https://yourdomain.com/accounts/oidc/<provider-id>/login/callback/
```

Replace `<provider-id>` with the **Provider ID** slug you set in the admin (e.g. `my-okta`). This is the URL your identity provider will redirect users back to after authentication.

## First-Time Signup via SSO

Whether a user logging in via SSO for the first time gets a local account created automatically is controlled by `ENABLE_SOCIAL_SIGNUPS` (`DJANGO_ENABLE_SOCIAL_SIGNUPS` as an environment variable), independently of [`ENABLE_SIGNUPS`](../usage/users.md#option-2-enable-user-self-registration), which only gates the regular email/password signup form. `ENABLE_SOCIAL_SIGNUPS` defaults to `true`, since access is typically already controlled by the identity provider itself.

## Email Verification and Authentication Settings

A few django-allauth settings that affect how social/SSO accounts interact with email verification and existing local accounts are also exposed as environment variables. Each is explained in detail in allauth's [social account configuration docs](https://docs.allauth.org/en/latest/socialaccount/configuration.html):

| Setting | Environment variable | Default | Accepted values |
|---|---|---|---|
| `ACCOUNT_EMAIL_VERIFICATION` | `DJANGO_ACCOUNT_EMAIL_VERIFICATION` | `optional` | `mandatory`, `optional`, `none` |
| `SOCIALACCOUNT_EMAIL_VERIFICATION` | `DJANGO_SOCIALACCOUNT_EMAIL_VERIFICATION` | `optional` | `mandatory`, `optional`, `none` |
| `SOCIALACCOUNT_EMAIL_AUTHENTICATION` | `DJANGO_SOCIALACCOUNT_EMAIL_AUTHENTICATION` | `False` | `True`, `False` |
| `SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT` | `DJANGO_SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT` | `False` | `True`, `False` |

- `*_EMAIL_VERIFICATION` controls whether a user must verify their email before the account is usable — `ACCOUNT_EMAIL_VERIFICATION` for regular signups, `SOCIALACCOUNT_EMAIL_VERIFICATION` for social/SSO signups.
- `SOCIALACCOUNT_EMAIL_AUTHENTICATION`, when `True`, treats a social login with a provider-verified email as a login to an existing local account with the same email, even if that account has no social account connected yet. Only enable this for identity providers you fully trust.
- `SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT`, when `True`, automatically connects the social account to the matched local account in that scenario, so the connection persists even if the email address later changes.
