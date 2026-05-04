
# FireScope Takeoff Portal V1

Private online passive fire click-to-count takeoff portal.

## What it does

- Private password gate
- Upload PDF / PNG / JPG drawings
- Click directly on penetrations/items
- Assign service, size, substrate and system
- Auto-price from rate library
- Edit takeoff register
- Summary by system, area and drawing
- Export Excel takeoff
- Export marked-up drawing PNG
- Online deployment ready

## Local Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Default local password:

```text
change-this-password
```

## Streamlit Cloud Deployment

1. Create a private GitHub repo.
2. Upload all files from this folder.
3. Go to Streamlit Cloud.
4. Create new app from repo.
5. Main file path: `app.py`.
6. Add a secret:

```toml
APP_PASSWORD = "your-private-password"
```

7. Deploy.

## Render Deployment

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

## Important

This is Version 1 private online app. It is not yet a full commercial SaaS product. For commercial release, add:
- Proper user accounts
- Database-backed saved projects
- Cloud file storage
- Organisation-level permissions
- Automated backups
- Full audit log
