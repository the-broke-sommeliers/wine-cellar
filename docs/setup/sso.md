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

## Callback URL

When registering the application with your identity provider, set the callback (redirect) URL to:

```
https://yourdomain.com/accounts/oidc/<provider-id>/login/callback/
```

Replace `<provider-id>` with the **Provider ID** slug you set in the admin (e.g. `my-okta`). This is the URL your identity provider will redirect users back to after authentication.
