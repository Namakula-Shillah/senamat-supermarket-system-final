# SENAMAT SUPERMARKET

## Supermarket Management System

**SENAMAT SUPERMARKET** is a web-based management system developed with Django to support supermarket operations, including product cataloguing, store and customer management, purchases, sales, stock monitoring, and receipt generation.

> **Academic project — Web Application Development.** The public deployment is intended for assessment and demonstration using sample data. See [Current status and known issue](#current-status-and-known-issue) before relying on the dashboard for operational records.

### Project links

- **Live website:** https://senamat-supermarket-system-final.onrender.com/
- **Source repository:** https://github.com/Namakula-Shillah/senamat-supermarket-system-final
- **Hosting:** Render (web service and PostgreSQL database, Frankfurt region)

## 1. Project information

| Item | Details |
| --- | --- |
| Project title | SENAMAT SUPERMARKET — Supermarket Management System |
| Institution | Islamic University in Uganda (Kampala Campus) |
| Programme | Bachelor of Information Technology |
| Course unit | Web Application Development |
| Lecturer | Mr. Walusimbi Abdul-Hakim |
| Project type | Academic web application |
| Django project | `supermarket` |
| Django application | `store` |
| Development database | SQLite |
| Hosted database | PostgreSQL (Render) |

### Group members

| No. | Full name | Registration number |
| --- | --- | --- |
| 1 | NAMAKULA SHILLAH | 224-063011-31887 |
| 2 | SSERUGYA FARIID | 224-063011-28296 |
| 3 | ATAYI GENDER SHUHAT | 224-063012-30123 |

## 2. Problem statement and objectives

Manual or fragmented supermarket recordkeeping can make it difficult to track available stock, manage sales and purchases consistently, and retrieve accurate operational information. SENAMAT provides a centralized interface for recording these activities and viewing their summaries.

The project aims to:

1. Maintain organized records for products, categories, customers, and stores.
2. Record purchases and sales with their associated line items.
3. Track inventory quantity for each product at each store.
4. Calculate transaction totals and adjust stock according to recorded transactions.
5. Display summary information and low-stock items on a dashboard.
6. Produce PDF sales receipts after sufficient payment is recorded.
7. Provide authenticated access and invitation-based user registration.

## 3. Functional modules

### Dashboard and reporting

The dashboard calculates counts for customers, products, categories, stores, purchases, and sales. It also shows total recorded inventory units, aggregate sales revenue, recent sales, and up to five low-stock entries (quantity **10 or fewer**).

### Categories, products, customers, and stores

- Create, view, update, and remove category records.
- Maintain product details such as item name, price, brand, model, color, and category.
- Register customers and view relevant customer details and spending summaries.
- Maintain supermarket store/branch records.

### Purchases and inventory

- Record supplier purchases and purchase line items.
- Associate purchased products with a destination store and quantity.
- Increase stock when purchase items are saved.
- Recalculate purchase totals based on quantities and unit prices.
- Display inventory per product and store.

### Sales and receipts

- Record sales and associated sale items.
- Deduct stock quantities for sales, subject to availability checks.
- Update calculated sale totals.
- Record payment amounts and generate PDF receipts when payment covers the total.

### Authentication and user administration

- User login and logout.
- Django administration interface.
- Invitation-code registration, using single-use five-digit codes generated through administrative functionality.
- A limit on repeated invalid invitation-code attempts.

## 4. Technology stack

| Component | Technology |
| --- | --- |
| Backend | Python 3.13, Django 6.1.2 |
| Frontend | Django templates, HTML, CSS, JavaScript, Bootstrap-based assets |
| Forms | `django-crispy-forms`, `crispy-bootstrap5` |
| PDF receipts | ReportLab |
| Local persistence | SQLite |
| Hosted persistence | PostgreSQL via `psycopg` and `dj-database-url` |
| Web server | Gunicorn |
| Static file serving | WhiteNoise |
| Hosting and deployment | Render connected to GitHub |
| Version control | Git and GitHub |

The authoritative dependency versions are in [`requirements.txt`](requirements.txt). The Python runtime family is selected by [`.python-version`](.python-version).

## 5. Repository structure

```text
web project final/
├── .gitignore
├── .python-version
├── README.md
├── requirements.txt
├── manage.py
├── bootstrap_demo_admin.py    # Create demo superuser if absent
├── start.sh                   # Migrate database and launch Gunicorn
├── supermarket/
│   ├── settings.py            # Environment-aware Django configuration
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── store/
    ├── admin.py
    ├── forms.py
    ├── models.py
    ├── views.py
    ├── middleware.py          # Authenticated HTML cache-control middleware
    ├── urls.py
    ├── tests.py
    ├── migrations/
    ├── templates/
    └── static/
```

Files such as `db.sqlite3`, local virtual environments, environment-variable files, and generated static output should not be committed to Git.

## 6. Local installation (Windows / VS Code)

### Requirements

Install Python, Git, and a code editor such as Visual Studio Code. Open a terminal in the directory containing `manage.py`.

```powershell
# Clone the repository if you do not already have it locally
git clone https://github.com/Namakula-Shillah/senamat-supermarket-system-final.git
cd senamat-supermarket-system-final

# Create and activate a local Python environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install the project dependencies
python -m pip install -r requirements.txt

# Prepare the local database
python manage.py migrate

# Optional: create an administrator account
python manage.py createsuperuser

# Verify configuration and run locally
python manage.py check
python manage.py runserver
```

If using the original Desktop folder rather than a Git clone, open `C:\Users\Administrator\Desktop\web project final` and run the commands starting from virtual-environment activation.

Useful local addresses:

- Login: http://127.0.0.1:8000/ or http://127.0.0.1:8000/login/ 
- Dashboard: http://127.0.0.1:8000/home/
- Django Admin: http://127.0.0.1:8000/admin/

The local database defaults to SQLite. Data entered locally is **not automatically copied** into the PostgreSQL database used by Render.

## 7. Typical usage workflow

1. Sign in using an authorized account.
2. Set up stores, product categories, products, and customers.
3. Create a supplier purchase and add the purchased items.
4. Review the updated inventory quantities for the relevant stores.
5. Create a customer sale and add sale items.
6. Record payment and generate a PDF receipt, if applicable.
7. Review operational totals, recent sales, and low-stock entries on the dashboard.

## 8. Main routes

| Route | Description |
| --- | --- |
| `/` and `/login/` | Sign-in |
| `/signup/` | Invitation-based account registration |
| `/home/` | Dashboard |
| `/category/` | Product categories |
| `/product/` | Products |
| `/customer/` | Customers |
| `/store/` | Stores/branches |
| `/inventory/` | Inventory overview |
| `/purchases/` | Purchases |
| `/purchase-item/` | Purchase line items |
| `/sales/` | Sales |
| `/sales-item/` | Sale line items |
| `/sales/<sale_id>/receipt/` | Sale receipt/payment workflow |
| `/about/` | About page |
| `/admin/` | Django administration |

## 9. Database and data integrity

The application includes models such as `Category`, `Customer`, `Product`, `Store`, `Inventory`, `Purchases`, `PurchaseItem`, `Sales`, `SalesItem`, and `SignupInvitation`.

Key business rules include stock adjustments on purchase/sale item changes, prevention of selling more items than are in stock, recalculation of transaction totals, and one-time signup invitations.

**Deployment database:** On Render, `supermarket/settings.py` requires a `DATABASE_URL` environment variable. The deployed application uses PostgreSQL for its database-backed records. The free web service's local filesystem should not be used as permanent business data storage.

## 10. Render deployment configuration

The GitHub repository contains the files used for deployment:

- `start.sh` runs migrations, attempts to provision a demonstration superuser, and starts `supermarket.wsgi:application` with Gunicorn.
- `bootstrap_demo_admin.py` reads demo account details from environment variables. It creates the account when missing; it does not overwrite an existing superuser's password.
- `.python-version` selects Python 3.13.
- `requirements.txt` includes Django, ReportLab, WhiteNoise, Gunicorn, PostgreSQL connectivity, and form-rendering packages.

### Web service settings

| Setting | Value |
| --- | --- |
| Runtime | Python |
| Region | Frankfurt (same as PostgreSQL) |
| Branch | `main` |
| Build command | `pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| Start command | `bash start.sh` |

### Required Render environment variables

| Name | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Secure Django secret key; must remain private |
| `DATABASE_URL` | Internal PostgreSQL connection string; must remain private |
| `DJANGO_SUPERUSER_USERNAME` | Temporary demo administrator username |
| `DJANGO_SUPERUSER_PASSWORD` | Temporary demo administrator password |
| `DJANGO_SUPERUSER_EMAIL` | Email associated with the demo account |

**Do not store the values of secrets or passwords in this README.** The lecturer-provided demonstration credentials are for temporary assessment only and should be changed or disabled afterward. Use fictional supermarket data in public demonstrations.

### Updating the deployed website

After making and testing local changes:

```powershell
git status
git add README.md
git commit -m "Update SENAMAT project documentation"
git push origin main
```

For application code changes, stage the actual changed code files as well. If automatic deployment is enabled, Render will redeploy the updated `main` branch; otherwise select **Manual Deploy → Deploy latest commit**.

## 11. Current status and known issue

**Status (17 November 2026):** The group has reported a successful Render deployment and confirmed that test records are retained in Django Admin. The cache-control middleware is registered in the local Django settings according to the supplied VS Code screenshot. Whether that exact revision is deployed and whether it corrects the issue remain unverified. There is an **unresolved dashboard record-display issue** that must be verified before final submission.

### Observed behavior

- Records appear immediately after saving through the SENAMAT dashboard.
- After navigating to another module and returning, previously saved records can be missing from the dashboard table.
- The same test record remains accessible through Django Admin.
- The behavior has been reported across multiple dashboard modules, not only Categories.

**Interpretation:** These observations show that the tested records were not lost from PostgreSQL. They do **not** yet prove whether the dashboard issue is caused by stale browser content, frontend rendering, or server-side response logic.

### Cache-control work under review

The repository includes `store/middleware.py` with `NoStoreForAuthenticatedHTMLMiddleware`. This middleware adds no-cache headers to authenticated HTML GET responses.

**Middleware registration (locally confirmed):** A VS Code screenshot shared on **17 November 2026** shows that the middleware is **already registered in the local** `supermarket/settings.py` immediately after Django's `AuthenticationMiddleware`:

```python
'django.contrib.auth.middleware.AuthenticationMiddleware',
'store.middleware.NoStoreForAuthenticatedHTMLMiddleware',
```

There is **no need to add it a second time**. The screenshot does **not** by itself establish that this exact settings change has been committed to GitHub and deployed on Render. Verify the deployed revision before assessing its effect:

```powershell
python manage.py check
git status
git add supermarket/settings.py store/middleware.py
git commit -m "Register authenticated dashboard cache-control middleware"
git push origin main
```

If Git says `nothing to commit`, check `git status` and the repository's `main` branch to confirm the change is already recorded. Then wait for the relevant Render deployment to show **Live** and repeat the navigation tests.

**Important:** This middleware is a **possible mitigation for cached HTML**, not a proven fix. Since the records remain in Django Admin, the investigation must also consider table rendering, template context, filters, and responses from the shared CRUD views. Keep the status as **unresolved until verified across all affected modules**.

### Verification procedure

1. Open the deployed SENAMAT application in a new browser session.
2. Save a unique **test** category or customer through the dashboard.
3. Confirm the saved record is present in Django Admin.
4. Navigate to another module, return, and check whether the record remains visible.
5. If it disappears, hard-refresh the page (`Ctrl + Shift + R`).
6. If it still disappears, inspect **View Page Source** for the test value:
   - **Present in HTML, absent on screen:** investigate frontend table/rendering behavior.
   - **Absent from HTML, present in Django Admin:** investigate the Django view, template context, filters, and relevant request logs.
7. Repeat on Categories, Products, Customers, Purchases, Sales, and Stores.
8. If the page source contains the record, also check whether a JavaScript table widget, search term, pagination, or client-side filter is hiding it.
9. Mark the issue resolved only after records remain visible across navigation, refreshes, and fresh sessions on the deployed site.

**Do not clear, reset, or recreate the PostgreSQL database as a troubleshooting shortcut.** Preserve existing data while investigating display behavior.

## 12. Testing and quality checks

Run locally:

```powershell
python manage.py check
python manage.py test store
```

Recommended acceptance checks include login, group-based access as configured, validation, category/product/customer/store operations, purchase and sale totals, inventory adjustments, receipt generation, and dashboard visibility across navigation and page reloads.

Passing automated tests alone is not proof that the deployed dashboard display problem has been resolved; browser-based tests against the deployed service are still required.

## 13. Known limitations and security notes

- **PDF receipt storage:** The current receipt generator writes PDFs to a local directory on the application server. Render's ephemeral filesystem does not provide permanent receipt storage; use external object storage if lasting PDFs are required.
- **Free hosting:** Free service/database lifecycle limits and sleeping behavior may affect demonstrations. Check current Render plan conditions and verify the deployed application shortly before assessment.
- **Environment separation:** Local SQLite records do not appear automatically in hosted PostgreSQL.
- **Data protection:** Do not publish real customer details, database connection URLs, secret keys, or administrator passwords.
- **Git hygiene:** Exclude `.env`, `db.sqlite3`, virtual environments, cache files, generated receipt PDFs, and generated static output. If sensitive data was committed earlier, remove it from history and rotate exposed secrets.
- **Status reporting:** Do not describe the dashboard record-display issue as fixed until live testing confirms it.

## 14. Future enhancements

Potential improvements include barcode scanning, more detailed role permissions, audit trails, inventory reorder alerts, richer analytics, improved receipt persistence, and expanded payment options. These are proposed improvements, not existing features.

---

**SENAMAT SUPERMARKET — Supermarket Management System**  
*Islamic University in Uganda, Kampala Campus — Web Application Development project.*
