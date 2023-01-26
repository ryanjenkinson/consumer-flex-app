# Consumer Flexibility App

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ryanjenkinson-consumerflex-dfs.streamlit.app/)
> ⚠️ This codebase is under active development. It is a personal side project of mine!

## Context

I wanted to build an app that uses open data from the energy system to demonstrate how consumers can be "flexible" in their energy usage. By "flexible", I mean that they demonstrate the potential to use energy at different times of day, according to some sort of signal. This signal could be:

1. A price signal
2. A one-off request to turn up or down (use more or less energy, in a given time window, in return for a reward)
3. A routine request to turn up or down (use more or less energy, in a given time window, in return for a reward)

The one-off or routing requests can come from their distribution service operator (DSO) or electricity system operator (ESO) - usually fulfilled through an intermediary such as their supplier or asset operator - to turn up or down.

Consumers will be at the heart of the future energy system. As we increasingly electrify our homes, we have enormous potential to use those devices more intelligently, for example by:

* Charging our electric vehicles at different times, avoiding periods of carbon-intensive generation and shifting to times of renewable generation (including [avoiding the need to pay for wind to be turned off](https://archy.deberker.com/the-uk-is-wasting-a-lot-of-wind-power/)!)
* Pre-heating our homes and managing heat more intelligently, from devices like heat pumps, to maximise shifting demand to cheaper, greener times and avoiding peaks.

### Motivating Example: The Demand Flexibility Service (DFS)

This winter, National Grid ESO implemented a service that suppliers can sign up to, where customers are emailed prior to the event and asked to turn down over a certain time window, if it is safe to do so. They are rewarded for doing this.

## How to run the app locally

Right now, there is only one app. It might grow to a series of apps in the future. You will need to install [`poetry`](https://python-poetry.org/).

Once installed, simply run:

1. `make setup` - uses poetry to install the dependencies, and installs pre-commit hooks
2. `make dfs-app` - runs the app locally

## How to contribute

If you are requesting a feature, you can file a Github Issue and I will respond. If you want to commit something, you can fork this repo and make a PR that I can review.
