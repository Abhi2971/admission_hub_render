import os
from app import create_app, socketio

# Create Flask app using factory
app = create_app()

# -----------------------
# ROOT ROUTE (Fix 404)
# -----------------------
@app.route("/")
def home():
    return {
        "status": "success",
        "message": "Admission Hub Backend Running 🚀",
        "api_base": "/api",
        "health": "/health"
    }

# -----------------------
# HEALTH CHECK ROUTE
# -----------------------
@app.route("/health")
def health():
    return {"status": "healthy"}

# -----------------------
# RUN SERVER (LOCAL ONLY)
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    # Use socketio instead of app.run for real-time features
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=True
    )