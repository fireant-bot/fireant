# fireant

**development**

[![Requirements Status](https://requires.io/enterprise/fireant-bot/fireant/requirements.svg?branch=main)](https://requires.io/enterprise/fireant-bot/fireant/requirements/?branch=main)
[![DeepSource](https://deepsource.io/gh/fireant-bot/fireant.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/fireant-bot/fireant/?ref=repository-badge)
[![license](https://img.shields.io/github/license/fireant-bot/fireant.svg?maxAge=2592000)](http://www.apache.org/licenses/LICENSE-2.0)
[![Jenkins](https://img.shields.io/jenkins/s/https/ci-builds.apache.org/job/Nutch/job/nutch-fireant.svg?maxAge=3600)](https://ci-builds.apache.org/job/Nutch/job/nutch-fireant/)

**docker**

*insert docker pulls / levels (?)*

<img src="https://www.freepnglogos.com/uploads/ant-png/funny-ant-thumbs-icon-transparent-png-svg-vector-29.png" width="300" />

fireant is a [Dependabot](https://dependabot.com/)-like service (tailored to [Apache Ant](https://ant.apache.org) + [Ivy](https://ant.apache.org/ivy) projects) which creates pull requests to keep your dependencies secure and up-to-date.

## Introduction and Context

This project intends to build upon the functionality for the existing Apache Nutch project.

> Apache Nutch is a well matured, production ready Web crawler. It enables fine grained configuration, relying on Apache Hadoop data structures, which are great for batch processing. Nutch is probably the most popular open-source Web search software with over 2.2k stars on Github.

## Project Motivation and Statement

This project will achieve two things
1. Vulnerability reduction: use existing tools to detect publicly disclosed security vulnerabilities associated with the project’s dependencies and establish a strategy for upgrading those dependencies.
2. Automate dependency management: implement a Dependabot-like capability which creates pull requests to keep the project dependencies secure and up-to-date.

Upon completion of this project, the resulting product(s) will be contributed to the Nutch project. However, the intended audience of this open source repo extends further to outside organizations (including JPL).

## Quickstart

First, take a look at the general overview of the [fireant codebase](https://github.com/fireant-bot/fireant/wiki/Codebase). After brief familiarization with the source code, take a shot at [running fireant](https://github.com/fireant-bot/fireant/wiki/Running-Fireant). This project also uses the Jenkins Pipeline to assist with automation; more information can be found [here](https://github.com/fireant-bot/fireant/wiki/Jenkins-Pipeline).




## Development

If you have issue using fireant, please log a ticket in our [Github issue tracker](https://github.com/fireant-bot/fireant/issues).

Contributions are always welcome! Feel free to contact our team below. 
	
- Matthew Treadwell - treadwem@usc.edu
- Randall Williams - rw15006@usc.edu	
- Jamie Mayer - jamesmey@usc.edu
- Mayram Nawaz - maryamna@usc.edu
- Teddy Lee - leetheod@usc.edu

## License