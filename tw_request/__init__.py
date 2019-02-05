from flask import Flask, redirect, url_for, render_template, request, make_response, session
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
from flask_login import logout_user
from bson.objectid import ObjectId
from urllib.parse import quote
import ssl
import pymongo
import datetime
import copy

app = Flask(__name__)
app.secret_key = "supersekrit"
_api_key="G4RfuppI0rf861TDF0Z8pKA4L"
_api_secret="A0gNyvH3R2441xR3IF5mWqHi7nKkt6ueZKmshp6aP3pJT8ZTSm"
blueprint = make_twitter_blueprint(
    api_key=_api_key,
    api_secret=_api_secret,
)
app.register_blueprint(blueprint, url_prefix="/login")

client=pymongo.MongoClient("mongodb://himyu:3o5sWuV9ld4YxVpE@tw-request-shard-00-00-giv8m.mongodb.net:27017,tw-request-shard-00-01-giv8m.mongodb.net:27017,tw-request-shard-00-02-giv8m.mongodb.net:27017/test?ssl=true&replicaSet=tw-request-shard-0&authSource=admin&retryWrites=true", connect=False, ssl_cert_reqs=ssl.CERT_NONE)
db=client.test

def update_user(request, resp):
  if twitter.authorized:
    if not request.cookies.get('userID'):
      rsp=make_response(resp)
      resp_settings = twitter.get("account/settings.json")
      assert resp_settings.ok
      _user=resp_settings.json()["screen_name"]
      rsp.set_cookie('userID', _user)
      return rsp
  return resp

@app.route("/")
def intro():
  if twitter.authorized:
    if not request.cookies.get('userID'):
      resp_settings = twitter.get("account/settings.json")
      assert resp_settings.ok
      _user=resp_settings.json()["screen_name"]
      resp=make_response(redirect("/user/{screen_name}".format(screen_name=_user)))
      resp.set_cookie('userID', _user)
      return resp
    else:
      return redirect("/user/{screen_name}".format(screen_name=request.cookies.get('userID')))
  else:
    return render_template('index.html')

@app.route("/login", methods=['POST'])
def login():
  if request.method=="POST":
    return redirect(url_for("twitter.login"))

@app.route("/logout")
def logout():
  if twitter.authorized:
    twitter.post("https://api.twitter.com/oauth/invalidate_token?access_token={access_token}&access_token_secret={access_token_secret}".format(access_token=_api_key, access_token_secret=_api_secret))
    resp=redirect(url_for("intro"))
    resp.set_cookie('userID', '', expires=0)
    del app.blueprints['twitter'].token
    session.clear()
    return resp
  else:  
    return redirect(url_for("intro"))

@app.route("/user/<username>")
def reveal_user(username):
  if not twitter.authorized:
    return redirect(url_for("intro"))
  global_username=request.cookies.get('userID')
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
  _pendingReq_l=list(db[username].find({"status": "Pending"}))
  _pendingReq_l.sort(key=lambda x: x["timestamp"], reverse=True)
  _completeReq_l=list(db[username].find({"status": "Complete"}))
  _completeReq_l.sort(key=lambda x: x["timestamp"], reverse=True)
  return render_template("generic.html", show_id=username, show_name=_show_name, view_id=_view_id, view_name=_view_name, description=_description, photoURL=_photoURL, pendingReq_l=_pendingReq_l, completeReq_l=_completeReq_l)


@app.route("/user/<username>", methods=["POST"])
def user_post(username):
  global_username=request.cookies.get('userID')
  resp_view_userinfo=twitter.get("users/show.json?screen_name={screen_name}".format(screen_name=global_username))
  assert resp_view_userinfo.ok
  _view_name=resp_view_userinfo.json()["name"]
  _message=str(request.form.get('message'))
  _isSecret=bool(request.form.get('isSecret'))
  _isAnonymous=bool(request.form.get('isAnonymous'))
  push_data={"author": _view_name,
             "author_id": global_username,
             "message": _message, 
             "isSecret": _isSecret,
             "isAnonymous": _isAnonymous,
             "timestamp": str(datetime.datetime.now()),
             "status": "Pending"}
  db[username].insert_one(push_data)
  return reveal_user(username)

@app.route("/me")
def me():
  if not twitter.authorized:
    return redirect(url_for("intro"))
  global_username=request.cookies.get('userID')
  resp_userinfo=twitter.get("users/show.json?screen_name={screen_name}".format(screen_name=global_username))
  assert resp_userinfo.ok
  _description=resp_userinfo.json()["description"]
  _photoURL=resp_userinfo.json()["profile_image_url_https"][:-11]+'.jpg'
  _name=resp_userinfo.json()["name"]
  _pendingReq_l=list(db[global_username].find({"status": "Pending"}))
  _pendingReq_l.sort(key=lambda x: x["timestamp"], reverse=True)
  _pendingReq_l_displayed=[]
  for req in _pendingReq_l:
    rq=copy.deepcopy(req)
    if len(req["message"])>30:
      rq["message"]=rq["message"][:27]+'...'
    _pendingReq_l_displayed.append(rq)
  _completeReq_l=list(db[global_username].find({"status": "Complete"}))
  _completeReq_l.sort(key=lambda x: x["timestamp"], reverse=True)
  return render_template("me.html", id=global_username, name=_name, photoURL=_photoURL, description=_description, pendingReq_l=_pendingReq_l, completeReq_l=_completeReq_l, pendingReq_l_displayed=_pendingReq_l_displayed)

@app.route("/me", methods=["POST"])
def me_post():
  global_username=request.cookies.get('userID')
  target_id=str(request.form.get('requests'))
  if not target_id:
    return me()
  target_req=db[global_username].find_one({"_id": ObjectId(target_id)})
  _isSecret=target_req["isSecret"]
  _isAnonymous=target_req["isAnonymous"]
  author_id=target_req["author_id"]
  action=str(request.form.get('request_action'))
  _isSharing=bool(request.form.get('isSharing'))
  target_req.pop('_id', None)
  if action=="accept":
    target_req['status']='Complete'
    db[global_username].replace_one({'_id': ObjectId(target_id)}, target_req)
  else:
    target_req['status']='Denied'
    db[global_username].replace_one({'_id': ObjectId(target_id)}, target_req)
  _post_text=("누군가" if _isAnonymous else ("@"+author_id))+" 의 리퀘스트가 "+("완료되었어요!!" if action=="accept" else "삭제되었어요 ㅜㅜ")
  print(str(_isSharing))
  print(_post_text)
  if not _isSharing:
    twitter.post("statuses/update.json?status={text}".format(text=quote(_post_text, safe='')))
  return me()

@app.route("/generic.html")
def generic():
  return render_template('generic.html')

@app.route("/elements.html")
def elements():
  return render_template('elements.html')