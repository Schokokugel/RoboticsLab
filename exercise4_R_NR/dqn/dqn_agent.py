import tensorflow as tf
import numpy as np
from dqn.replay_buffer import ReplayBuffer
from carracing_utils import (STRAIGHT,
                             LEFT,
                             RIGHT,
                             ACCELERATE,
                             BRAKE,
                             get_action_name)

class DQNAgent:

    def __init__(self, game_name, Q, Q_target, num_actions, discount_factor=0.99,
                 batch_size=64, epsilon=0.05,
                 distribution=np.array([0.2, 0.2, 0.2, 0.2])):
        """
         Q-Learning agent for off-policy TD control using Function Approximation.
         Finds the optimal greedy policy while following an epsilon-greedy policy.

         Args:
            Q: Action-Value function estimator (Neural Network)
            Q_target: Slowly updated target network to calculate the targets.
            num_actions: Number of actions of the environment.
            discount_factor: gamma, discount factor of future rewards.
            batch_size: Number of samples per batch.
            epsilon: Chance to sample a random action. Float betwen 0 and 1.
        """
        self.game_name = game_name

        self.Q = Q
        self.Q_target = Q_target

        self.epsilon = epsilon
        self.distribution = distribution

        self.num_actions = num_actions
        self.batch_size = batch_size
        self.discount_factor = discount_factor

        # define replay buffer
        self.replay_buffer = ReplayBuffer(capacity=1.3*1e3)

        # Start tensorflow session
        self.sess = tf.Session()
        self.sess.run(tf.global_variables_initializer())

        self.saver = tf.train.Saver()


    def train(self, state, action, next_state, reward, terminal, skip_learning=False):
        """
        This method stores a transition to the replay buffer and updates the Q networks.
        """

        # 1. add current transition to replay buffer
        self.replay_buffer.add_transition(state, action, next_state, reward, terminal)
        if skip_learning:
            return

        # 2. sample next batch and perform batch update:
        n_b_states, n_b_actions, n_b_next_states, n_b_rewards, n_b_dones = self.replay_buffer.next_batch(self.batch_size)
        # print("n_b_dones.shape:\n\t{}".format(n_b_dones.shape))
        #       2.1 compute td targets:
        #           td_target =  reward + discount * max_a Q_target(next_state_batch, a)
        prediction = self.Q_target.predict(self.sess, n_b_next_states)
        # print("prediction.shape:\n\t{}".format(prediction.shape))
        target = np.max(prediction, axis=1)
        # print("target.shape:\n\t{}".format(target.shape))
        td_target = n_b_rewards
        # print("td_target.shape:\n\t{}".format(td_target.shape))


        # print("target[n_b_dones==0].shape:\n\t{}".format(target[n_b_dones==0].shape))
        td_target[n_b_dones==0] += np.dot(self.discount_factor, target[n_b_dones==0])
        # print("n_b_rewards:\t{}".format(n_b_rewards))
        # print("td_target:\t{}".format(td_target))

        #       2.2 update the Q network
        #              self.Q.update(...)
        # loss = self.Q.update(self.sess, n_b_states, n_b_actions, td_target)
        self.Q.update(self.sess, n_b_states, n_b_actions, td_target)
        #       2.3 call soft update for target network
        #              self.Q_target.update(...)
        self.Q_target.update(self.sess)
        # return loss

    def act(self, state, deterministic):
        """
        This method creates an epsilon-greedy policy based on the Q-function approximator and epsilon (probability to select a random action)
        Args:
            state: current state input
            deterministic:  if True, the agent should execute the argmax action (False in training, True in evaluation)
        Returns:
            action id
        """
        r = np.random.uniform()
        if deterministic or r > self.epsilon:
            # take greedy action (argmax)
            prediction = self.Q.predict(self.sess, [state])
            action_id = np.argmax(prediction)
            # print("action_id:\t{}".format(action_id))
        else:
            # sample random action
            # Hint for the exploration in CarRacing: sampling the action from a uniform distribution will probably not work.
            # You can sample the agents actions with different probabilities (need to sum up to 1) so that the agent will prefer to accelerate or going straight.
            # To see how the agent explores, turn the rendering in the training on and look what the agent is doing.
            if self.game_name == "CartPole-v0":
                action_id = np.random.randint(0, self.num_actions)
            elif self.game_name == "MountainCar-v0":
                action_id = np.random.randint(0, self.num_actions)
            elif self.game_name == "CarRacing-v0":
                value = np.random.random_sample()
                # LEFT, RIGHT, ACCELERATE, BRAKE, (STRAIGHT)
                distribution_sum = np.cumsum(self.distribution)
                action_id = 0
                for i in range(4):
                    if value <= distribution_sum[i]:
                        action_id = i + 1
                        break

            # print("Picked random action: {}".format(get_action_name(action_id)))
        return action_id


    def load(self, file_name):
        self.saver.restore(self.sess, file_name)
