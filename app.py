import argparse
from flask import Flask 
from routes import app
from display import db

def main():
    app.run(debug=True)

if __name__ == '__main__':
     main()

# def create_app():
# 	return app