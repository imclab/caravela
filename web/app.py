import os
import sys
import json

from flask import (
  Flask, 
  render_template, 
  make_response,
  request,  
  jsonify
)

from . import assets
from . import tasks


app = Flask(__name__)
assets.init(app)

def sort(iter, col, dir="ASC"):
  if dir == "ASC":
    reversed = False
  elif dir == "DESC":
    reversed = True

  return sorted(iter, key=lambda r:r[col], reverse=reversed)

def execute(q_str, col=1):
  results = tasks.count.delay(q_str).get()
  return sort(results, col=col)

def ensure_dir(path):
  dirname = os.path.dirname(path)
  if not os.path.exists(dirname):
    os.makedirs(dirname)

@app.template_filter('value')
def value(k):
  return k.split(':',1)[-1]

@app.template_filter('commas')
def commas(val):
  return "{:,d}".format(val)

@app.route('/')
def index():
  # this call should be cached
  relations = tasks.relations.delay().get()

  return render_template(
    'index.html',
    features = relations,
  )



@app.route('/schemas')
def schema():
  # todo: if it's safe todo so move this transformation
  # to tasks.py
  relations = [ 
    dict(id=name, name=name, fields=schema['fields'])
    for name, schema in tasks.relations.delay().get()
  ]

  return jsonify(schemas=relations)


  
@app.route('/query')
def query_endpoint():

  q = request.args['q']

  results = tasks.query.delay(q).get()
  response = make_response(results)
  response.headers['content-type'] = "application/json"
  return response

def query_from(insight):
  statement = json.loads(insight['content'])['query']
  return dict(
    id=insight['id'],
    name=insight['id'],
    statement=statement,
    insight=insight['id']
  )

def sideload(records):
  insights = []
  queries = []

  for insight in records:
    insight['query'] = insight['id']
    insights.append(insight)
    queries.append(query_from(insight))

  return dict(
    insights=insights,
    queries=queries
  )

@app.route("/insights")
def list_insights():
  #return jsonify(insights=list(insights.all()))
  res = sideload(insights.all())

  return jsonify(**res)

@app.route("/insights/<id>")
def get_insight(id):
  insight = insights.get(id)
  return jsonify(
    insight=insight,
    query=query_from(insight)
  )

from . import insights