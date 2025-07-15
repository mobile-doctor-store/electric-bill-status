from app import app

# For Vercel deployment
def handler(request):
    return app(request.environ, start_response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
