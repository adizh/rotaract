from app import create_app

app = create_app()

# Define the handler for Vercel
# def handler(event, context):
#     from mangum import Mangum
#     asgi_app = Mangum(app)
#     return asgi_app(event, context)

if __name__ == '__main__':
    app.run(debug=True)