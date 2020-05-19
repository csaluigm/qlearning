import pickle
import time
import numpy as np
import argparse
import re

from envs import TradingEnv
from agent import DQNAgent
from utils import get_data, get_scaler, maybe_make_dir
import matplotlib.pyplot as plt
import pandas as pd

from plotly.subplots import make_subplots
import plotly.graph_objects as go

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-e', '--episode', type=int, default=20,
                      help='number of episode to run')
  parser.add_argument('-b', '--batch_size', type=int, default=32,
                      help='batch size for experience replay')
  parser.add_argument('-i', '--initial_invest', type=int, default=20000,
                      help='initial investment amount')
  parser.add_argument('-m', '--mode', type=str, required=True,
                      help='either "train" or "test"')
  parser.add_argument('-w', '--weights', type=str, help='a trained model weights')
  args = parser.parse_args()

  maybe_make_dir('weights')
  maybe_make_dir('portfolio_val')

  timestamp = time.strftime('%Y%m%d%H%M')

  data = np.around(get_data())
  train_data = data[:, :10]
  test_data = data[:, 10:]


  plt.plot(train_data[0])

  plt.show()

  env = TradingEnv(train_data, args.initial_invest)
  state_size = env.observation_space.shape
  action_size = env.action_space.n
  agent = DQNAgent(state_size, action_size)
  scaler = get_scaler(env)

  portfolio_value = []

  if args.mode == 'test':
    # remake the env with test data
    env = TradingEnv(test_data, args.initial_invest)
    # load trained weights
    agent.load(args.weights)
    # when test, the timestamp is same as time when weights was trained
    timestamp = re.findall(r'\d{12}', args.weights)[0]

  for e in range(args.episode):
    state = env.reset()
    state = scaler.transform([state])
    for time in range(env.n_step):
      action = agent.act(state)
      next_state, reward, done, info = env.step(action)
      next_state = scaler.transform([next_state])
      if args.mode == 'train':
        agent.remember(state, action, reward, next_state, done)
      state = next_state
      if done:
        print("episode: {}/{}, episode end value: {}".format(
          e + 1, args.episode, info['cur_val']))
        portfolio_value.append(info['cur_val']) # append episode end portfolio value
        break
      if args.mode == 'train' and len(agent.memory) > args.batch_size:
        agent.replay(args.batch_size)
    if args.mode == 'train' and (e + 1) % 10 == 0:  # checkpoint weights
      agent.save('weights/{}-dqn.h5'.format(timestamp))


  hold_data = np.asarray(agent.qs[0]).reshape(args.episode,(train_data.size)-1)
  buy_data = np.asarray(agent.qs[1]).reshape(args.episode,(train_data.size)-1)
  sell_data = np.asarray(agent.qs[2]).reshape(args.episode,(train_data.size)-1)
  action_data = np.asarray(agent.qs[3]).reshape(args.episode,(train_data.size)-1)


  def get_scatter(data):
      # import plotly.express as px
      
      plots = []

      for action in data:
          
          Z = []
          Y = []  
          X = []
          rownum = 0
          
          for row in action:
              colnum = 0
              for col in row:
                  Z.append(rownum)
                  Y.append(col)
                  X.append(colnum)
                  colnum += 1
              rownum += 1
          plots.append(go.Scatter3d(x=X, y=Z, z=Y, mode='lines+markers'))

      return plots

  # fig = go.Figure(data=plots)
  # fig.show()


  fig = make_subplots(rows=1, cols=2,
  specs=[[{"type": "scene"}, {"type": "xy"}]])



  # get_poly(hold_data)
  scatter_plots = get_scatter([hold_data,buy_data,sell_data,action_data])

  for p in scatter_plots:
    fig.add_trace(
      p,
      row=1, col=1
    )

  fig.show()

  # portfolio.performance.net_worth.plot()

  plt.show()

  # save portfolio value history to disk
  with open('portfolio_val/{}-{}.p'.format(timestamp, args.mode), 'wb') as fp:
    pickle.dump(portfolio_value, fp)