"""DQN Algorithm. Tested with CARLA.
You can visualize experiment results in ~/ray_results using TensorBoard.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import ray
from ray import tune
from carla_env import CarlaEnv
from ray.rllib.models.modelv2 import ModelV2
from ray.rllib.models.catalog import ModelCatalog
from ray.rllib.models.tf.fcnet import FullyConnectedNetwork
from ray.tune import grid_search, run_experiments
from helper.CarlaHelper import kill_server
import tensorflow as tf
import gc
import time
import argparse

ENV_CONFIG = {"RAY": True, "DEBUG_MODE": False}  # Are we running an experiment in Ray

env_config = ENV_CONFIG.copy()
env_config.update(
    {
        "RAY": True,  # Are we running an experiment in Ray
        "DEBUG_MODE": False,
        "Experiment": "experiment2",

    }
)

def first_run(args):
    try:
        kill_server()
        tf.keras.backend.clear_session()
        ray.init()
        run_experiments({
            args.name: {
                "run": args.model,
                "env": CarlaEnv,
                "stop": {"perf/ram_util_percent":90.0}, # {"training_iteration":300},
                "checkpoint_freq": 10,
                "checkpoint_at_end":True,
                "local_dir": args.directory,
                "config": {
                    "env_config": env_config,
                    "num_gpus_per_worker": 0.5,
                    "num_cpus_per_worker":4,
                    "buffer_size": 1000,
                    "num_workers": 1,
                    "model": {
                        'dim': 300,
                        'conv_filters': [
                            [16, [8, 8], 4],
                            [32, [4, 4], 2],
                            [32, [4, 4], 2],
                            [64, [19, 19], 1],
                        ],
                    },
                },
            },
        },
        resume = False,
        )
        ray.shutdown()
        gc.collect()
    finally:
        kill_server()
        ray.shutdown()

def find_latest_checkpoint(args):
    """
    Finds the latest checkpoint, based on how RLLib creates and names them.
    """
    start = args.directory+"/"+args.name
    max_f = ""
    max_g = ""
    max_checkpoint = 0
    for f in os.listdir(start):
        if args.model in f:
            temp = start+"/"+f
            for g in os.listdir(temp):
                if "checkpoint" in g:
                    episode = int(''.join([n for n in g if n.isdigit()]))
                    if episode > max_checkpoint:
                        max_checkpoint = episode
                        max_f = f
                        max_g = g
    if max_checkpoint == 0:
        print("Could not find any checkpoint, make sure that you have selected the correct folder path")
        raise IndexError
    start+=("/"+max_f+"/"+max_g+"/"+max_g.replace("_","-"))
    return start


def restore_run(args):
    try:
        while (True):
            kill_server()
            tf.keras.backend.clear_session()
            checkpoint = find_latest_checkpoint(args)
            ray.init()
            run_experiments({
                args.name: {
                    "run": args.model,
                    "env": CarlaEnv,
                    "stop": {"perf/ram_util_percent":90.0},
                    "checkpoint_freq": 10,
                    "checkpoint_at_end" : True,
                    "local_dir": args.directory,
                    "restore": checkpoint,
                    "config": {
                        "env_config": env_config,
                        "num_gpus_per_worker": 0.5,
                        "num_cpus_per_worker":4,
                        "buffer_size": 1000,
                        "num_workers": 1,
                        "model": {
                            'dim': 300,
                            'conv_filters': [
                                [16, [8, 8], 4],
                                [32, [4, 4], 2],
                                [32, [4, 4], 2],
                                [64, [19, 19], 1],
                            ],
                        },
                    },
                },
            },
            resume = False,
            )
            ray.shutdown()
            gc.collect()

    finally:
        kill_server()
        ray.shutdown()

def main():
    argparser = argparse.ArgumentParser(
        description=__doc__)
    argparser.add_argument(
        '-d', '--directory',
        metavar='D',
        default= os.path.expanduser("~")+"/ray_results/newdir",
        help='Specified directory to save results')
    argparser.add_argument(
        '-n', '--name',
        metavar='P',
        default="dqn",
        help='Name of the experiment')
    argparser.add_argument(
        '-m', '--model',
        metavar='P',
        default="DQN",
        help='Model used by the experiment (default: DQN)')
    argparser.add_argument(
        '--restore',
        action='store_true',
        default=False,
        help='If we need to restore from the specified directory')
    args = argparser.parse_args()

    gc.enable()
    if not args.restore:
        if os.path.exists(args.directory):
            if len(os.listdir(args.directory)) != 0:
                print("The directory " + args.directory + " is not empty. To start a new training instance, make sure this folder is either empty or non-existing.")
                return
        first_run(args)
    if args.restore:
        if not(os.path.exists(args.directory)) or len(os.listdir(args.directory)) == 0:
            print("You can't restore from an empty or non-existing directory. To restore a training instance, make sure there is at least one checkpoint.")
    restore_run(args)

if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print('\ndone.')
