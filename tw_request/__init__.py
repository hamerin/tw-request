from flask import Flask, redirect, url_for, render_template, request, make_response, session, jsonify, abort
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
from bson.objectid import ObjectId
from urllib.parse import quote
import ssl
import pymongo
import datetime
import copy
import os

app = Flask(__name__)
app.secret_key = "supersekrit"
_api_key = os.environ['TWITTER_API_KEY']
_api_secret = os.environ['TWITTER_API_SECRET']
blueprint = make_twitter_blueprint(
    api_key=_api_key,
    api_secret=_api_secret,
)
app.register_blueprint(blueprint, url_prefix="/login")

client = pymongo.MongoClient(
    os.environ['MONGODB_URL'], connect=False, ssl_cert_reqs=ssl.CERT_NONE)
db = client.test


@app.route("/")
def intro():
    if twitter.authorized:
        if not request.cookies.get('userID'):
            resp_settings = twitter.get("account/settings.json")
            assert resp_settings.ok

            user = resp_settings.json()["screen_name"]

            resp = make_response(
                redirect("/user/{screen_name}".format(screen_name=user)))
            resp.set_cookie('userID', user)
            return resp
        else:
            return redirect("/user/{screen_name}".format(screen_name=request.cookies.get('userID')))
    else:  # Not Authorized
        return render_template('index.html')


@app.route("/login", methods=['POST'])
def login():
    if request.method == "POST":
        return redirect(url_for("twitter.login"))


@app.route("/logout")
def logout():
    if twitter.authorized:
        twitter.post("https://api.twitter.com/oauth/invalidate_token?access_token={access_token}&access_token_secret={access_token_secret}".format(
            access_token=_api_key, access_token_secret=_api_secret))
        del app.blueprints['twitter'].token

        session.clear()

        resp = redirect(url_for("intro"))
        resp.set_cookie('userID', '', expires=0)
        return resp
    else:
        return redirect(url_for("intro"))


@app.route("/user/<username>")
def reveal_user(username):
    try:
        if not twitter.authorized:
            return redirect(url_for("intro"))

        global_username = request.cookies.get('userID')

        resp_show_userinfo = twitter.get(
            "users/show.json?screen_name={screen_name}".format(screen_name=username))
        assert resp_show_userinfo.ok

        resp_view_userinfo = twitter.get(
            "users/show.json?screen_name={screen_name}".format(screen_name=global_username))
        assert resp_view_userinfo.ok

        if username == global_username:
            return redirect("me")

        view_id = global_username
        description = resp_show_userinfo.json()["description"]
        photoURL = resp_show_userinfo.json(
        )["profile_image_url_https"][:-11]+'.jpg'
        show_name = resp_show_userinfo.json()["name"]
        view_name = resp_view_userinfo.json()["name"]

        return render_template("user.html",
                               show_id=username,
                               show_name=show_name,
                               view_id=view_id,
                               view_name=view_name,
                               description=description,
                               photoURL=photoURL)

    except AssertionError:  # If user not exists
        abort(404)


@app.route("/user_ajax/<username>", methods=["GET"])
def user_ajax(username):
    pendingReq_l = list(db[username].find({"status": "Pending"}))
    pendingReq_l.sort(key=lambda x: x["timestamp"], reverse=True)
    completeReq_l = list(db[username].find({"status": "Complete"}))
    completeReq_l.sort(key=lambda x: x["timestamp"], reverse=True)

    return jsonify({"html": render_template("user_ajax.html",
                                            pendingReq_l=pendingReq_l,
                                            completeReq_l=completeReq_l)})


@app.route("/user_ajax/<username>", methods=["POST"])
def user_ajax_post(username):
    global_username = request.cookies.get('userID')

    resp_view_userinfo = twitter.get(
        "users/show.json?screen_name={screen_name}".format(screen_name=global_username))
    assert resp_view_userinfo.ok

    view_name = resp_view_userinfo.json()["name"]
    message = str(request.form.get('message'))
    isSecret = bool(request.form.get('isSecret'))
    isAnonymous = bool(request.form.get('isAnonymous'))

    db[username].insert_one({"author": view_name,
                             "author_id": global_username,
                             "message": message,
                             "isSecret": isSecret,
                             "isAnonymous": isAnonymous,
                             "timestamp": str(datetime.datetime.now()),
                             "status": "Pending"})

    return user_ajax(username)


@app.route("/me")
def me():
    if not twitter.authorized:
        return redirect(url_for("intro"))

    global_username = request.cookies.get('userID')

    resp_userinfo = twitter.get(
        "users/show.json?screen_name={screen_name}".format(screen_name=global_username))
    assert resp_userinfo.ok

    description = resp_userinfo.json()["description"]
    photoURL = resp_userinfo.json()["profile_image_url_https"][:-11]+'.jpg'
    name = resp_userinfo.json()["name"]

    return render_template("me.html",
                           id=global_username,
                           name=name,
                           photoURL=photoURL,
                           description=description)


@app.route("/me_ajax", methods=["GET"])
def me_ajax():
    global_username = request.cookies.get('userID')

    pendingReq_l = list(db[global_username].find({"status": "Pending"}))
    pendingReq_l.sort(key=lambda x: x["timestamp"], reverse=True)
    pendingReq_l_displayed = []
    for req in pendingReq_l:
        rq = copy.deepcopy(req)
        if len(req["message"]) > 30:
            rq["message"] = rq["message"][:27]+'...'
        pendingReq_l_displayed.append(rq)

    completeReq_l = list(db[global_username].find({"status": "Complete"}))
    completeReq_l.sort(key=lambda x: x["timestamp"], reverse=True)

    return jsonify({"html": render_template("me_ajax.html",
                                            pendingReq_l=pendingReq_l,
                                            completeReq_l=completeReq_l,
                                            pendingReq_l_displayed=pendingReq_l_displayed)})


@app.route("/me_ajax", methods=["POST"])
def me_ajax_post():
    global_username = request.cookies.get('userID')

    target_id = str(request.form.get('requests'))
    if target_id == 'None':
        return me_ajax()

    else:  # If target exists
        target_req = db[global_username].find_one({"_id": ObjectId(target_id)})
        isSecret = target_req["isSecret"]
        isAnonymous = target_req["isAnonymous"]
        author_id = target_req["author_id"]
        action = str(request.form.get('request_action'))
        isntSharing = bool(request.form.get('isSharing'))

        target_req.pop('_id', None)

        if action == "accept":
            target_req['status'] = 'Complete'
            db[global_username].replace_one(
                {'_id': ObjectId(target_id)}, target_req)
        else:  # action == "discard"
            target_req['status'] = 'Denied'
            db[global_username].replace_one(
                {'_id': ObjectId(target_id)}, target_req)

        post_text = ("누군가" if isAnonymous else ("@"+author_id)) + \
            " 의 리퀘스트가 "+("완료되었어요!!" if action == "accept" else "삭제되었어요 ㅜㅜ")
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
