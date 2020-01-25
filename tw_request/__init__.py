from flask import Flask, redirect, url_for, render_template, request, make_response, session, jsonify, abort
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
from bson.objectid import ObjectId
from urllib.parse import quote
import ssl
import pymongo
import datetime
import time
import copy
import os

app = Flask(__name__)
app.secret_key = "supersekrit"

f = open('tw_request/.env', 'r')


def getKey(): return f.readline().split('=',1)[1].strip()


api_key = getKey()
api_secret = getKey()
blueprint = make_twitter_blueprint(api_key=api_key, api_secret=api_secret)
app.register_blueprint(blueprint, url_prefix="/login")

client = pymongo.MongoClient(getKey(),
                             connect=False,
                             ssl_cert_reqs=ssl.CERT_NONE)
db = client.main
cache = client.cache

f.close()


def authorization_required(fun):
    def decorated(*args):
        if not twitter.authorized:
            abort(401)
        return fun(*args)
    return decorated


def getinfo_id(id) -> dict:
    try:
        ret = cache['twd'].find_one({"id_str": str(id)})
        isCreated = bool(ret)

        if not ret or time.time() - ret['_timestamp'] > 86400:
            ret = twitter.get(
                f"users/show.json?user_id={id}").json()
            ret['profile_image_url_https'] = ret['profile_image_url_https'].replace(
                '_normal', '')
            ret['_timestamp'] = time.time()

        if isCreated:
            cache['twd'].update({'_id': ObjectId(ret['_id'])}, {'$set': ret})
        else:
            cache['twd'].insert_one(ret)
        return ret
    except:
        return {}


def getinfo_name(name) -> dict:
    try:
        ret = cache['twd'].find_one({"screen_name": name})
        isCreated = bool(ret)

        if not ret or time.time() - ret['_timestamp'] > 86400:
            ret = twitter.get(
                f"users/show.json?screen_name={name}").json()
            ret['profile_image_url_https'] = ret['profile_image_url_https'].replace(
                '_normal', '')
            ret['_timestamp'] = time.time()

        if isCreated:
            cache['twd'].update({'_id': ObjectId(ret['_id'])}, {'$set': ret})
        else:
            cache['twd'].insert_one(ret)
        return ret
    except:
        return {}


@authorization_required
def getinfo() -> dict:
    try:
        userinfo = dict()
        if 'userid' in session:
            userid = session['userid']
            userinfo = getinfo_id(userid)
        else:
            account = twitter.get("account/verify_credentials.json")
            assert account.ok

            userinfo = getinfo_id(account.json()["id"])

        assert userinfo
        return userinfo
    except AssertionError:
        abort(500)


@app.route("/")
def intro():
    if twitter.authorized:
        userinfo = getinfo()
        if not 'userid' in session:
            session['userid'] = userinfo["id"]

        return redirect(f"/user/{userinfo['screen_name']}")

    else:
        return render_template('index.html')


@app.route("/login")
def login():
    return redirect(url_for("twitter.login"))


@authorization_required
@app.route("/logout")
def logout():
    invaildate_url = f"https://api.twitter.com/oauth/invalidate_token?access_token={api_key}&access_token_secret={api_secret}"
    twitter.post(invaildate_url)
    del app.blueprints["twitter"].token
    session.clear()

    return redirect(url_for("intro"))


@authorization_required
@app.route("/user/<username>")
def reveal_user(username):
    try:
        viewUser = getinfo()
        showUser = getinfo_name(username)

        if viewUser['id'] == showUser['id']:
            return redirect("/me")

        return render_template("user.html",
                               show_scname=showUser['screen_name'],
                               show_name=showUser['name'],
                               description=showUser['description'],
                               photoURL=showUser['profile_image_url_https'],
                               view_scname=viewUser['screen_name'],
                               view_name=viewUser['name'])

    except AssertionError:  # If user not exists
        abort(400)


@authorization_required
@app.route("/user_ajax/<username>", methods=["GET"])
def user_ajax(username):
    showUser = getinfo_name(username)

    pendingRequests = list(db[showUser['id_str']].find({"status": "Pending"}))
    pendingRequests.sort(key=lambda x: x["timestamp"], reverse=True)
    for req in pendingRequests:
        authorUser = getinfo_id(req['author_id'])
        req['author_scname'] = authorUser['screen_name']
        req['author_name'] = authorUser['name']

    completeRequests = list(
        db[showUser['id_str']].find({"status": "Complete"}))
    completeRequests.sort(key=lambda x: x["timestamp"], reverse=True)
    for req in completeRequests:
        authorUser = getinfo_id(req['author_id'])
        req['author_scname'] = authorUser['screen_name']
        req['author_name'] = authorUser['name']

    return jsonify({"html": render_template("user_ajax.html",
                                            pendingRequests=pendingRequests,
                                            completeRequests=completeRequests)})


@authorization_required
@app.route("/user_ajax/<username>", methods=["POST"])
def user_ajax_post(username):
    viewUser = getinfo()
    showUser = getinfo_name(username)

    message = str(request.form.get('message'))
    isSecret = bool(request.form.get('isSecret'))
    isAnonymous = bool(request.form.get('isAnonymous'))

    db[showUser['id_str']].insert_one({"author_id": viewUser["id_str"],
                                       "message": message,
                                       "isSecret": isSecret,
                                       "isAnonymous": isAnonymous,
                                       "timestamp": str(datetime.datetime.now()),
                                       "status": "Pending"})

    return user_ajax(username)


@authorization_required
@app.route("/me")
def me():
    viewUser = getinfo()

    return render_template("me.html",
                           scname=viewUser['screen_name'],
                           name=viewUser['name'],
                           photoURL=viewUser['profile_image_url_https'],
                           description=viewUser['description'])


@authorization_required
@app.route("/me_ajax", methods=["GET"])
def me_ajax():
    viewUser = getinfo()

    pendingRequests = list(db[viewUser['id_str']].find({"status": "Pending"}))
    pendingRequests.sort(key=lambda x: x["timestamp"], reverse=True)
    for req in pendingRequests:
        authorUser = getinfo_id(req['author_id'])
        req['author_scname'] = authorUser['screen_name']
        req['author_name'] = authorUser['name']

    pendingRequests_disp = []
    for req in pendingRequests:
        rq = copy.deepcopy(req)
        if len(req["message"]) > 30:
            rq["message"] = rq["message"][:27]+'...'
        pendingRequests_disp.append(rq)

    completeRequests = list(
        db[viewUser['id_str']].find({"status": "Complete"}))
    completeRequests.sort(key=lambda x: x["timestamp"], reverse=True)
    for req in completeRequests:
        authorUser = getinfo_id(req['author_id'])
        req['author_scname'] = authorUser['screen_name']
        req['author_name'] = authorUser['name']

    return jsonify({"html": render_template("me_ajax.html",
                                            pendingRequests=pendingRequests,
                                            pendingRequests_disp=pendingRequests_disp,
                                            completeRequests=completeRequests)})


@authorization_required
@app.route("/me_ajax", methods=["POST"])
def me_ajax_post():
    viewUser = getinfo()

    targetId = str(request.form.get('requests'))
    if targetId == 'None':
        return me_ajax()

    else:  # If target exists
        target_req = db[viewUser['id_str']].find_one(
            {"_id": ObjectId(targetId)})
        isSecret = target_req["isSecret"]
        isAnonymous = target_req["isAnonymous"]
        author_id = target_req["author_id"]
        timestamp = target_req["timestamp"]
        action = str(request.form.get('request_action'))
        isntSharing = bool(request.form.get('isSharing'))

        if action == "accept":
            db[viewUser['id_str']].update(
                {"_id": ObjectId(targetId)},
                {"$set":
                    {
                        'status': 'Complete'
                    }
                 }
            )
        else:  # action == "discard"
            db[viewUser['id_str']].update(
                {"_id": ObjectId(targetId)},
                {"$unset": target_req}
            )

        post_text = timestamp.split('.')[0] + "에 신청된 " + \
            ("누군가" if isAnonymous else (f"@{getinfo_id(author_id)['screen_name']} ")) + \
            "의 리퀘스트가 "+("완료되었어요!!" if action == "accept" else "삭제되었어요...")

        if not isntSharing:  # If user wants to share
            twitter.post(
                "statuses/update.json?status={text}".format(text=quote(post_text, safe='')))

        return me_ajax()


@app.route("/elements")
def elements():
    return render_template('elements.html')


@app.errorhandler(404)
def error404(e):
    return render_template("404.html"), 404
