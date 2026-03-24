# 1. Clone the repository

First thing first, clone the repository.

```
git clone https://github.com/neural-maze/realtime-phone-agents-course.git
cd realtime-phone-agents-course
```

# 2. Install uv

Instead of `pip` or `poetry`, we are using `uv` as the Python package manager. 

To install uv, simply follow this [instructions](https://docs.astral.sh/uv/getting-started/installation/). 

# 3. Install the project dependencies

Once uv is intalled, you can install the project dependencies. First of all, let's create a virtual environment.

```bash
uv venv .venv
. .venv/bin/activate # or source .venv/bin/activate
uv pip install -e .
```

Just to make sure that everything is working, simply run the following command:

```bash
 uv run python --version
```

# 4. Environment Variables

Now that all the dependencies are installed, it's time to populate the `.env` file with the correct values.
To help you with this, we have created a `.env.example` file that you can use as a template.

```
cp .env.example .env
```

Now, you can open the `.env` file with your favorite text editor and set the correct values for the variables.
Right now, you'll see the following variables to be set:

```
GROQ_API_KEY=YOUR_GROQ_KEY_GOES_HERE
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=openai/gpt-oss-20b
```

We provide support for Groq out of the box, but you can add additional providers if you extend the repository with your own fork.

> 🛠️ Or just open a PR if you think more people would benefit from this!

We selected `gpt-oss-20b` because it's one of Groq's "production" models and offered solid response quality along with fast token generation. You're free to use any model you prefer, of course.

Just keep in mind: if you opt for slower, heavy-reasoning models, the call experience may suffer.

Consider this your warning! 🤣

### Groq

To create the GROQ_API_KEY, and be able to interact with Groq models, you just need to follow this [instructions](https://console.groq.com/docs/quickstart).

![alt text](img/groq_api_key.png)

Once you have created the API key, you can copy it and paste it into an `.env` file (following the same format as the `.env.example` file).

As for the `GROQ__BASE_URL` and the `GROQ__MODEL`, you can leave the defaults from the `.env.example`.

### OpenAI

To leverage Superlinked's natural queries, we'll make use of OpenAI models (in particular, `gpt-4o-mini`).

Simply add your OpenAI API Key to the `OPENAI__API_KEY` var in your `.env` file.

# 5. Twilio 

You can hook up a Stream to a SIP provider like Twilio, which lets you give your app its own phone number.

[Sign up on Twilio](https://www.twilio.com/) and buy a phone number with voice support. If you’re on a trial account, you'll receive a free phone number (that's what we've done for our experiments).

Don't worry about creating TwiML Apps, or enabling the connection between Twilio and our API, as we will cover that in detail as part of the course.

# 6. Ngrok

For local development, you’ll need a public HTTPS URL so Twilio can reach your API. Since your FastAPI server is running on your machine, Twilio can't access it directly — which is why we use [ngrok](https://ngrok.com/).

Go to [ngrok's website](https://ngrok.com/), sign up, and grab your auth token. You'll need it to run ngrok without restrictions.

After installing ngrok and adding your auth token, expose your local server with:

```
ngrok http <port>
```

Don't worry about this, as we have a `Makefile` command to expose the correct port when the time comes. We'll cover this in the course too.
