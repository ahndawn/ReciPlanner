# ReciPlanner

## Description

This application is a web-based platform designed to help users find recipes based on their dietary restrictions and preferences. It uses the Spoonacular API to search for recipes and provides details about each recipe, including the ingredients required and the cooking instructions.

## Installation

1. Clone this repository using the following command in your terminal:

    ```bash
    git clone https://github.com/ahndawn/ReciPlanner.git
    ```

2. Navigate to the project directory:

    ```bash
    cd ReciPlanner
    ```

3. Install the necessary dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Set your Spoonacular API key as an environment variable:

- On Unix/Linux/MacOS:

    ```bash
    export SPOON_API=your_api_key
    ```

- On Windows:

    ```cmd
    set SPOON_API=your_api_key
    ```

Replace `your_api_key` with your actual API key.

## Usage

To start the application, run:

```bash
flask run
