# Import libraries
# Pika is a pure-Python implementation of the AMQP 0-9-1 protocol.
# Random is a Python built-in library for generating pseudo-random numbers.
# Time provides various time-related functions. In this code, it is used to introduce a delay between connection attempts to RabbitMQ.
# Json provides methods to manipulate JSON data. In this code, it is used to convert a tuple of strings into a JSON string.
# Os provides the getenv function.
# Sympy is a Python library for symbolic mathematics. It provides the 'randprime()' function, which generates a random prime number in a given range. In this code, 'randprime()' is used to generate two random prime numbers.
import pika
import random
import time
import json
import os
from sympy import randprime

# Ensure the Prover has access to RabbitMQ.  This mechanism attempts to establish a
# connection to RabbitMQ multiple times over a set duration.
max_attempts = 10
attempts = 0
wait_time = 5

while attempts < max_attempts:
    try:
        # Establish a connection to RabbitMQ server. The connection is blocking which means
        # that the network operations are on hold until they complete or timeout.
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='rabbitmq',
                credentials=pika.PlainCredentials('test', 'test'),
                blocked_connection_timeout=300
            )
        )
        # If connection is established, break the loop.
        break

    except Exception as e:
        print(f"Attempt {attempts+1} failed. Retrying...")
        attempts += 1
        time.sleep(wait_time)

if attempts == max_attempts:
    print("Max attempts reached. Could not establish a connection.")
    exit()

# Open a new channel with RabbitMQ.
channel = connection.channel()

# Declare a queue to receive the challenges.
channel.queue_declare(queue='challenge')


# Define a range for the prime numbers
lower_bound = 10000
upper_bound = 100000

# Generate two random prime numbers 'p' and 'q' within the defined range
p = randprime(lower_bound, upper_bound)
q = randprime(lower_bound, upper_bound)

# Calculate 'n' as product of 'p' and 'q'
n = p * q

# Generate random number 's' in the range of 2 and n-1
s = random.randint(2, n-1)

# Calculate 'v'
v = (s * s) % n

# Convert 'n' and 'v' to string and convert to json
n_str = str(n)
v_str = str(v)
nv_json_str = json.dumps((n_str, v_str))

# Send 'n' and 'v' to the Verifier through queue 'init'
print(f"Sending 'n': {n} and 'v': {v} to Verifier\n", flush=True)
channel.basic_publish(exchange='', routing_key='init', body=nv_json_str)


# This closure creates and returns another function - 'callback', that has access to the argument 'r'.
def make_callback(r):
    def callback(ch, method, properties, body):
        # This inner function (callback) computes and sends the response 'y',
        # which is based on the received challenge 'b' and the value 'r'.
        b = int(body)
        y = (r * s ** b) % n
        print(f"  Received challenge: {b}.  Sending response: {y}", flush=True)
        channel.basic_publish(exchange='', routing_key='response', body=str(y))
        channel.basic_cancel(consumer_tag='challenge')
    return callback

# This function is used as the callback for the 'challenge' queue. It creates a callback function using
# the current 'r' value.  Without this function 'r' is not consistent inside the callback.
def process_message(ch, method, properties, body):
    global current_r
    callback = make_callback(current_r)
    callback(ch, method, properties, body)

# Tell RabbitMQ that this function should receive messages from the 'challenge' queue.
channel.basic_consume(queue='challenge', on_message_callback=process_message, auto_ack=True)

# Specify total number of iterations of the protocol (configured in .env). Fallback to '20' if not set
totalTests = int(os.getenv('TOTAL_TESTS') or '20')

# The main loop for the Prover side of the Fiat-Shamir protocol.
for i in range(totalTests):
    print(f"Iteration: {i+1}", flush=True)

    # A random integer 'r' is generated for each iteration.
    current_r = random.randint(1, n-1)
    x = (current_r * current_r) % n

    # The computed commitment 'x' is sent to the 'commitment' queue.
    print(f"  Generated r: {current_r}, x: {x}. Sending commitment {x}...", flush=True)
    channel.basic_publish(exchange='', routing_key='commitment', body=str(x))

    # Process data events to handle incoming messages.
    channel._process_data_events(time_limit=3)

print("\nAll iterations completed.", flush=True)
