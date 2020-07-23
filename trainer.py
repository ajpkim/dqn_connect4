import numpy as np
import pdb
import torch
import torch.nn as nn

from deep_q_agent import DeepQAgent
from self_play_episodes import self_play_episodes
from mdp import Connect4MDP


class Trainer:
    """
    ... 
    """
    def __init__(self, agent=DeepQAgent(), lr=.005, gamma=.99, batch_size=64, eps_max=1, eps_min=.1, eps_freq=10000, eps_decrement=.01, *args, **kwargs):
        self.mdp = Connect4MDP()
        self.agent = agent
        self.optimizer = torch.optim.Adam(params=agent.policy_net.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()
        self.lr = lr
        self.gamma = gamma
        self.batch_size = batch_size
        self.eps_max = eps_max
        self.eps_min = eps_min
        self.eps_freq = eps_freq
        self.eps_decrement = eps_decrement
        self.eps = lambda learning_iter: max(self.eps_min, 
                                            self.eps_max - (learning_iter/self.eps_freq) * self.eps_decrement)

    def self_play(self, n_episodes):
        """
        Generate training data by playing games vs self.
        Gathers experiece tuples over n_episodes and pushes them to agent replay buffer.
        """        
        eps = self.eps(self.agent.learning_iters)
        experiences = self_play_episodes(self.mdp, self.agent, n_episodes, eps)
        
        ### DEBUGGIN WITH EPS == 0        
        # experiences = self_play_episodes(self.mdp, self.agent, n_episodes, 0)
               
        for state, action, reward, next_state, done in experiences:
            self.agent.replay_buffer.push(state, action, reward, next_state, done)

    def learn(self):
        """
        Update model with random batch from agent replay buffer.
        """
        batch = self.agent.replay_buffer.sample(self.batch_size)
        states = torch.tensor([x.state for x in batch]).float().to(self.agent.device)
        actions = [x.action for x in batch]
        rewards = torch.tensor([x.reward for x in batch]).float().to(self.agent.device)
        next_states = torch.tensor([x.next_state for x in batch]).float().to(self.agent.device)
        dones = [x.done for x in batch]

        self.optimizer.zero_grad()
        q_vals = self.agent.policy_net(states)[range(len(actions)), actions]  # Q vals for paths taken
        q_next_vals = self.agent.target_net(next_states)
        q_next_vals[dones] = 0  # terminal states have no future expected value
        q_targets = rewards + self.gamma * torch.max(q_next_vals, dim=1)[0]

        all_q_vals = self.agent.policy_net(states)



        # print()
        # print('actions')
        # print(actions)
        # print()
        # print('original all q vals')
        # print(self.agent.policy_net(states)) 
        # print(self.agent.policy_net(states).shape)
        # print()
        # print('QVALS:', q_vals)
        # print(q_vals.shape)
        # print('\n\n')
        # print('QTARGETS:', q_targets)
        # print(q_targets.shape)

        # breakpoint()


        loss = self.loss_fn(q_targets, q_vals).to(self.agent.device)
        loss.backward()
        self.optimizer.step()

        self.agent.learning_iters += 1
        if self.agent.learning_iters % self.agent.update_target_freq == 0:
            self.agent.update_target_net()

    def train(self, iters, n_episodes):
        """
        Train agent over given number of iterations. Each iteration consists 
        of self play over n_episodes and then a learn step where agent 
        updates network based on random sample from replay buffer
        """
        for i in range(iters):
            self.self_play(n_episodes)
            self.learn()
    
    def __repr__(self):
        return f'Trainer for {self.agent.name}'
