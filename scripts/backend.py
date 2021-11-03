import pyrebase

config = {
  "apiKey": "AIzaSyAVL9OlUxeg4ACKJS3l-i-qY6aJ-Bkee_4",
  "authDomain": "cs3237-motion-detection.firebaseapp.com",
  "databaseURL": "https://cs3237-motion-detection-default-rtdb.asia-southeast1.firebasedatabase.app/",
  "storageBucket": "cs3237-motion-detection.appspot.com"
}

email = "nguyen2001ag2@gmail.com"
password = "nguyen752001"

print("I reached here")
firebase = pyrebase.initialize_app(config)
print("I have initilized the app")

def main():
  print("Im in main")
  auth = firebase.auth()
  # print("Now i log in")
  # Log the user in
  # user = auth.sign_in_with_email_and_password(email, password)
  # print("I have successfully logged in")

  # Get a reference to the database service
  db = firebase.database()

  # data to save
  data = {
      "name": "Nguyen 'Sirui' Trang"
  }

  # Pass the user's idToken to the push method
  # results = db.child("users").push(data, user['idToken'])
  results = db.child("users").push(data)
  print("Finish publishing")
  return

# if __name__ == '__main__':
main()