from app import create_app

app = create_app()

# This is the WSGI application entry point for Vercel
app.debug = False
