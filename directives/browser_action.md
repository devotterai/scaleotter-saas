# Browser Action

## Goal
Automate browser interactions to perform tasks on websites (e.g., "Go to amazon.com and find the price of iPhone 15").

## Inputs
- `task`: A natural language description of the browser actions to perform.

## Tools
- `execution/browser_automation.py`

## Outputs
- Console logs of the browser actions.
- The final result of the task.

## Steps
1.  Run `python execution/browser_automation.py "<task>"`.
2.  Monitor the browser window (if visible) or logs.
