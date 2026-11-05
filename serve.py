import sys, os, json
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from flask import Flask, request, jsonify, render_template
mode=sys.argv[1]; root=Path(__file__).parent/mode
sys.path.insert(0,str(root))
engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
with patch.dict(os.environ,{'DATABASE_URL':'sqlite://','CONSUMER_KEY':'test','CONSUMER_SECRET':'test'}), patch('sqlalchemy.create_engine',return_value=engine):
 import display
for n in ('rooms','group_ids'): display.User.__table__.c[n].type=JSON()
display.User.__table__.create(engine)
session=sessionmaker(bind=engine)(); display.db_session=session
session.add(display.User(username='proof',rooms=[123,123],group_ids=[]));session.commit()
app=Flask(__name__,template_folder=str(root/'templates'),static_folder=str(root/'static'))
state={'fail':False,'requests':[]}
@app.context_processor
def helpers():
 def url_for(name,**kw):
  return '/static/'+kw['filename'] if name=='static' else {'addToFavorites':'/addtofavorites','removeFromFravorites':'/removefromfavorites'}.get(name,'/'+name)
 return dict(url_for=url_for)
@app.route('/')
def index(): return render_template('availablerooms.html',username='proof')
@app.route('/queryrooms')
def rooms():
 session.expire_all(); saved=session.query(display.User).first().rooms
 room=dict(room_id=123,building='Blair',room_no='B41',favorite=123 in saved,occupancy='2',sq_footage=200,res_college='Mathey',average_rating=4,number_of_reviews=1,bathroom='Private',ac='Yes',floor=1,elevator='Yes',independent_only=False)
 return jsonify(data=[room],recordsTotal=1,recordsFiltered=1,draw=1)
@app.route('/addtofavorites',methods=['POST'])
@app.route('/removefromfavorites',methods=['POST'])
def favorite():
 state['requests'].append(request.path)
 if state['fail']: return 'error',500
 (display.addFavorite if request.path=='/addtofavorites' else display.removeFavorite)(json.loads(request.data),'proof')
 return 'success'
@app.route('/__state',methods=['GET','POST'])
def status():
 if request.method=='POST':
  values=request.json
  if 'rooms' in values:
   session.query(display.User).first().rooms=values.pop('rooms');session.commit()
  state.update(values)
 session.expire_all()
 return jsonify(**state,rooms=session.query(display.User).first().rooms)
@app.route('/<path:path>',methods=['GET','POST'])
def other(path): return jsonify({})
app.run(port=int(sys.argv[2]),threaded=False)
