# Objective_agent
I tried to build an agent that does whatever you ask him by giving him just a prompt with LangChain.
I managed to connect it to my Google account, allowing him to access my Google Suite (Drive, Gmail...) by calling their API.
The script allows one agent to modify a python file, creating a new function for the action the user asked for (if it determines that there is no function for the task asked). This way, the next agent can execute the function for the task asked.

Nonetheless, I understimated the complexity of the project. Explaining an llm exactly what they should do and how should they output it is really difficult. Why? Because if one doesn't output what you wanted it to output, the next agent input will be different than what it was specified to receive. Consequently, the whole chain breaks.

In spite of that, I learnt a lot in this project about how AI agents really work. At the end, they are llms with memory and tools (python functions).
