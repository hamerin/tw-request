from flask import Flask, redirect, url_for, render_template, request
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
from flask_login import logout_user

app = Flask(__name__)
app.secret_key = "supersekrit"
blueprint = make_twitter_blueprint(
    api_key="G4RfuppI0rf861TDF0Z8pKA4L",
    api_secret="A0gNyvH3R2441xR3IF5mWqHi7nKkt6ueZKmshp6aP3pJT8ZTSm",
)
app.register_blueprint(blueprint, url_prefix="/login")

global_username=None

@app.route("/")
def intro():
  global global_username
  if twitter.authorized:
    if global_username==None:
      resp_settings = twitter.get("account/settings.json")
      assert resp_settings.ok
      global_username=resp_settings.json()["screen_name"]
    return redirect("/user/{screen_name}".format(screen_name=global_username))
  else:
    return render_template('index.html')

@app.route("/login", methods=['POST'])
def login():
  if request.method=="POST":
    return redirect(url_for("twitter.login"))

@app.route("/logout")
def logout():
  logout_user()
  return redirect(url_for("/"))

@app.route("/user/<username>")
def reveal_user(username):
  global global_username
  if not twitter.authorized:
    return redirect(url_for("/"))
  if not global_username:
    resp_settings = twitter.get("account/settings.json")
    assert resp_settings.ok
    global_username=resp_settings.json()["screen_name"]
  resp_show_userinfo=twitter.get("users/show.json?screen_name={screen_name}".format(screen_name=username))
  assert resp_show_userinfo.ok
  resp_view_userinfo=twitter.get("users/show.json?screen_name={screen_name}".format(screen_name=global_username))
  assert resp_view_userinfo.ok
  if username==global_username:
    return redirect("me")
  _view_id=global_username
  _description=resp_show_userinfo.json()["description"]
  _photoURL=resp_show_userinfo.json()["profile_image_url_https"][:-11]+'.jpg'
  _show_name=resp_show_userinfo.json()["name"]
  _view_name=resp_view_userinfo.json()["name"]
  return render_template("generic.html", show_id=username, show_name=_show_name, view_id=_view_id, view_name=_view_name, description=_description, photoURL=_photoURL)

@app.route("/me")
def me():
  global global_username
  if not twitter.authorized:
    return redirect(url_for("/"))
  if not global_username:
    resp_settings = twitter.get("account/settings.json")
    assert resp_settings.ok
    global_username=resp_settings.json()["screen_name"]
  return render_template("elements.html")

@app.route("/generic.html")
def generic():
  return render_template('generic.html')

@app.route("/elements.html")
def elements():
  return render_template('elements.html')