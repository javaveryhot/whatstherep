import os, pymongo, communities, logging, re, time, urllib.parse, math, random, uuid, hashlib, datetime
from flask import Flask, request, render_template, redirect, abort, make_response
app = Flask("app", template_folder="templates")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60

mdb_client = pymongo.MongoClient(os.getenv("MONGODB_CONNECTION_URL"))

heavy_db = mdb_client.heavy

accounts_col = heavy_db.accounts # Collection for the community accounts (not WTR accounts)
reputations_col = heavy_db.reputations # Collection for each rating/review
tokens_col = heavy_db.tokens

logging.getLogger("werkzeug").setLevel(logging.ERROR)

@app.route("/")
def __homepage():
  return render_template("/home.html", communities=communities.settings)

@app.route("/<community>/<uid>")
def __user_reputation(community, uid):
  if community not in communities.settings:
    abort(404)
  doc = accounts_col.find_one({"community": community, "id_methods.value": neutralize(uid)})
  if doc is None:
    return redirect(f"/create/{community}/{urllib.parse.quote_plus(uid)}")
  good_reps = reputations_col.count_documents({"user": doc.get("_id"), "positive": True})
  total_reps = reputations_col.count_documents({"user": doc.get("_id")})
  rep_score = calculate_rep_score(good_reps, total_reps)
  rep_value = calculate_rep_value(good_reps, total_reps)
  has_created_review = reputations_col.count_documents({"user": doc.get("_id"), "author": request.cookies.get("auth_token")}) != 0 if "auth_token" in request.cookies else False
  tagged_reviews = reputations_col.find({"tags.0": {"$exists": True}})
  tag_popularity = {}
  total_tags = 0
  for tagged_review in tagged_reviews:
    for individual_tag in tagged_review["tags"]:
      if individual_tag in tag_popularity:
        tag_popularity[individual_tag] += 1
      else:
        tag_popularity[individual_tag] = 1
      total_tags += 1
  best_tag = None
  if total_tags > 5:
    max_val = 0
    for i in range(0, len(tag_popularity)):
      if list(tag_popularity.values())[i] > max_val:
        max_val = i
    best_tag = list(tag_popularity.keys())[max_val]
  return render_template("reputation.html",
    meta=doc,
    reputations=reputations_col.find({"user": doc.get("_id")}),
    communities=communities.settings,
    id_query=uid,
    safe_id_query=urllib.parse.quote_plus(uid),
    rep_score=rep_score,
    rep_score_color=get_rep_score_hex_color(rep_score),
    rep_score_label=get_rep_score_label(rep_score),
    rep_value=rep_value,
    good_reps=good_reps,
    total_reps=total_reps,
    has_created_review=has_created_review,
    own_review=reputations_col.find_one({"user": doc.get("_id"), "author": request.cookies.get("auth_token")}) if has_created_review else None,
    reviews=reputations_col.find({"user": doc.get("_id"), "author": {"$not": {"$eq": request.cookies.get("auth_token") if has_created_review else None}}}),
    best_tag=best_tag
  )

@app.route("/create/<community>/<uid>")
def __create_user_page(community, uid):
  if community not in communities.settings:
    abort(404)
  return render_template("new_reputation_page.html", community=community, id_query=uid, communities=communities.settings, regex=re, safe_id_query=urllib.parse.quote_plus(uid))

@app.route("/create/<community>/<uid>/submit", methods=["POST"])
def __commit_create_user_page(community, uid):
  if community not in communities.settings:
    abort(404)
  if accounts_col.count_documents({"community": community, "id_methods.value": neutralize(uid)}) != 0:
    return redirect(f"/{community}/{uid}" + warning_context_suffix("User already registered! You have been redirected to their reputation page."))
  community_settings = communities.settings[community]
  id_methods_save = []
  i = 0
  for id_method in community_settings["id_methods"]:
    method_value = request.form.get(f"id_method_{i}")
    if method_value is not None and re.match(id_method["regex"], method_value) is not None:
      if accounts_col.count_documents({"community": community, "id_methods.value": neutralize(method_value)}):
        return redirect(f"/create/{community}/{uid}" + error_context_suffix(f"The value for \"{id_method['label']}\" was found already belonging to someone else in the {communities.settings[community]['name']} community. Please see if that registered user is who you are trying to set up now, or edit their page if that data belongs to this user now."))
      id_methods_save.append({"index": i, "value": method_value})
    elif id_method["mandatory"]:
      abort(404)
    i += 1
  accounts_col.insert_one({
    "community": community,
    "id_methods": id_methods_save,
    "created": time.time()
  })
  return redirect(f"/{community}/{uid}")

@app.route("/<community>/<uid>/add-reputation", methods=["POST"])
def __submit_review(community, uid):
  if community not in communities.settings:
    abort(404)
  doc = accounts_col.find_one({"community": community, "id_methods.value": neutralize(uid)})
  if doc is None:
    abort(404)
  positive_rep = request.form.get("reputation") == "1"
  review_text = request.form.get("review_text") or None
  if review_text and len(review_text) > 200:
    abort(404)
  community_settings = communities.settings[community]
  reputation_tags = []
  i = 0
  for tag in community_settings["tags"]:
    if request.form.get(f"tag_{i}") == "on":
      reputation_tags.append(i)
    i += 1
  response = make_response(redirect(f"/{community}/{urllib.parse.quote_plus(uid)}" + success_context_suffix("Your review was submitted successfully!")))
  review_id = str(uuid.uuid4())
  token_lifespan = 60 * 60 * 24 * 30
  author_id = None
  if "auth_token" in request.cookies:
    auth_token = request.cookies.get("auth_token")
    doc_token = tokens_col.find_one({"_id": auth_token, "expire": {"$gt": time.time()}})
    if doc_token is not None:
      response.set_cookie("auth_token", auth_token, max_age=token_lifespan)
      tokens_col.update_one({"_id": auth_token}, {"$set": {"expire": time.time() + token_lifespan}})
      author_id = auth_token
  if author_id is None:
    if tokens_col.count_documents({"ip_address": enhash(request.remote_addr), "expire": {"$gt": time.time()}}) >= 2:
      return redirect(f"/{community}/{urllib.parse.quote_plus(uid)}" + error_context_suffix("Your IP address already has two existing authentication tokens and is not eligible for another one at the moment. Please use an already existing one or wait for them to expire."))
    tokens_col.delete_many({"expire": {"$lt": time.time()}})
    author_id = str(uuid.uuid4())
    response.set_cookie("auth_token", author_id, max_age=token_lifespan)
    tokens_col.insert_one({
      "_id": author_id,
      "ip_address": enhash(request.remote_addr),
      "expire": time.time() + token_lifespan
    })
  if reputations_col.count_documents({"user": doc.get("_id"), "$or": [{"author": author_id}, {"ip_address": enhash(request.remote_addr)}]}) > 0:
    return redirect(f"/{community}/{urllib.parse.quote_plus(uid)}" + error_context_suffix("You or someone on your IP address has already submitted a reputation for this user. You cannot submit another one."))
  if reputations_col.count_documents({"date": {"$gt": time.time() - 60 * 2}, "$or": [{"author": author_id}, {"ip_address": enhash(request.remote_addr)}]}):
    return redirect(f"/{community}/{urllib.parse.quote_plus(uid)}" + error_context_suffix("You or someone on your IP address has already submitted a reputation on WhatsTheRep.net very recently. You cannot submit another one for a while."))
  reputations_col.insert_one({
    "_id": review_id,
    "user": doc.get("_id"),
    "positive": positive_rep,
    "text": review_text,
    "tags": reputation_tags,
    "author": author_id,
    "ip_address": enhash(request.remote_addr),
    "date": time.time()
  })
  return response

@app.route("/search", methods=["POST"])
def __form_redirect():
  community = request.form.get("community")
  uid = request.form.get("uid")
  return redirect(f"/{community}/{urllib.parse.quote_plus(uid)}")

@app.errorhandler(404)
def __page_not_found(e):
  return render_template("errors/404.html")

@app.errorhandler(500)
def __internal_server_error(e):
  return render_template("errors/500.html")

cache_context_messages = {}

@app.context_processor
def __context_injector():
  return dict(grab_context_message_cache=grab_context_message_cache, timestamp_to_string=timestamp_to_string)

def message_context_cacher(class_name, text):
  global cache_context_messages
  if len(cache_context_messages) > 5:
    cache_context_messages = {}
  pointer = str(random.randint(10**2, 10**3))
  cache_context_messages[pointer] = [class_name, text]
  return pointer

def grab_context_message_cache(pointer):
  return cache_context_messages.get(pointer)

def custom_context_suffix(class_name, text):
  return "?ctx=" + message_context_cacher(class_name, text)

def error_context_suffix(text):
  return custom_context_suffix("error", text)

def warning_context_suffix(text):
  return custom_context_suffix("warning", text)

def success_context_suffix(text):
  return custom_context_suffix("success", text)

def timestamp_to_string(timestamp):
  return datetime.datetime.fromtimestamp(timestamp).strftime("%m/%d/%Y")

def calculate_rep_score(good_reps, total_reps):
  return round((good_reps / total_reps) * 100) if total_reps != 0 else None

def get_rep_score_hex_color(score):
  if score is None:
    return "#6f5771"
  score /= 100
  bottom_color = (163, 38, 35)
  top_color = (163, 247, 60)
  rgb = (
      math.floor(bottom_color[0] + score * (top_color[0] - bottom_color[0])),
      math.floor(bottom_color[1] + score * (top_color[1] - bottom_color[1])),
      math.floor(bottom_color[2] + score * (top_color[2] - bottom_color[2]))
  )
  return "#%02x%02x%02x" % rgb

def get_rep_score_label(score):
  if score is None:
    return "Unrated"
  labels = [
    [100, "Perfect"],
    [95, "Great"],
    [75, "Good"],
    [60, "Okay"],
    [30, "Bad"],
    [20, "Really bad"],
    [0, "Terrible"],
  ]
  for label_info in labels:
    if score >= label_info[0]:
      return label_info[1]

def calculate_rep_value(good_reps, total_reps):
  return good_reps - (total_reps - good_reps)

def neutralize(string):
  return re.compile("^" + re.escape(string) + "$", re.IGNORECASE)

def enhash(string):
    return hashlib.md5(bytes(string, "utf-8")).hexdigest()

app.run(host="0.0.0.0", port=8080)