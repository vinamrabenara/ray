"""Example of running a custom hand-coded policy alongside trainable policies.

This example has two policies:
    (1) a simple PG policy
    (2) a hand-coded policy that acts at random in the env (doesn't learn)

In the console output, you can see the PG policy does much better than random:
Result for PG_multi_cartpole_0:
  ...
  policy_reward_mean:
    pg_policy: 185.23
    random: 21.255
  ...
"""

import argparse
import gym
import os

import ray
from ray import tune
from ray.tune.registry import register_env
from ray.rllib.examples.env.multi_agent import MultiAgentCartPole
from ray.rllib.examples.policy.random_policy import RandomPolicy
from ray.rllib.utils.test_utils import check_learning_achieved

parser = argparse.ArgumentParser()
parser.add_argument(
    "--framework",
    choices=["tf", "tf2", "tfe", "torch"],
    default="tf",
    help="The DL framework specifier.")
parser.add_argument(
    "--as-test",
    action="store_true",
    help="Whether this script should be run as a test: --stop-reward must "
    "be achieved within --stop-timesteps AND --stop-iters.")
parser.add_argument(
    "--stop-iters",
    type=int,
    default=20,
    help="Number of iterations to train.")
parser.add_argument(
    "--stop-timesteps",
    type=int,
    default=100000,
    help="Number of timesteps to train.")
parser.add_argument(
    "--stop-reward",
    type=float,
    default=150.0,
    help="Reward at which we stop training.")

if __name__ == "__main__":
    args = parser.parse_args()
    ray.init()

    # Simple environment with 4 independent cartpole entities
    register_env("multi_agent_cartpole",
                 lambda _: MultiAgentCartPole({"num_agents": 4}))
    single_env = gym.make("CartPole-v0")
    obs_space = single_env.observation_space
    act_space = single_env.action_space

    stop = {
        "training_iteration": args.stop_iters,
        "episode_reward_mean": args.stop_reward,
        "timesteps_total": args.stop_timesteps,
    }

    config = {
        "env": "multi_agent_cartpole",
        "multiagent": {
            "policies": {
                "pg_policy": (None, obs_space, act_space, {
                    "framework": args.framework,
                }),
                "random": (RandomPolicy, obs_space, act_space, {}),
            },
            "policy_mapping_fn": (
                lambda aid, **kwargs: ["pg_policy", "random"][aid % 2]),
        },
        "framework": args.framework,
        # Use GPUs iff `RLLIB_NUM_GPUS` env var set to > 0.
        "num_gpus": int(os.environ.get("RLLIB_NUM_GPUS", "0")),
    }

    results = tune.run("PG", config=config, stop=stop, verbose=1)

    if args.as_test:
        check_learning_achieved(results, args.stop_reward)

    ray.shutdown()
