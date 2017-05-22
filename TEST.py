import os
import psutil
import numpy
from math import *
from string import Template
import matplotlib.pyplot as plt

"""Funksjoner for testing av applikasjon"""

def memory_info():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss/10**6

def print_memory_info():
    print()
    print("************************")
    print("Minnebruk: {} MB".format(memory_info()))
    print("************************")
    print()



if __name__ == "__main__":
    lastsituasjon = {"Ulykkeslast": {"psi_T": 1.0, "psi_S": 0, "psi_V": 0}}
    if "Ulykkeslast" in lastsituasjon:
        print("JAU")
    else:
        print("nei")











