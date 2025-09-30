I want a cli tool that I can call to review PRs. 

I should be able to either specify a path to directory that is a git repo or otherwise leverage cwd and assume it's a git repo.

The tool will get the git diff relative to the branching point from `main`.

It will supply this and any other user-supplied files or text as extra context to a prompt to one or more llms. 

there is a tool that we should use for making the requests to the llm. it's called nllm. you can see the source here: ~/Development/nllm

one should be able to configure the llm reviewer models with a config file or by explicitly passing the models as args

something like this:

```
models:
  - name: "gpt-4.1"
    options: ["-o", "temperature", "0.7", "--system", "You are a helpful and concise assistant"]
  - name: "gemini-2.5-flash-preview-05-20"
    options: ["-o", "temperature", "0.3"]
  - name: "claude-opus-4.1"
    options: ["-o", "temperature", "0.2", "--system", "Be precise and analytical"]

defaults:
  retries: 1
```

these are effectively overriding the configs / args expected and passed through to nllm. reason being, someone should be able to independently configure nllm for generic prompting for a repo but then also have overriding specifications for code reviewing that will be leveraged when git-reviewer is called.

the user should optionally be able to specify a path where all of the reviews land. this is done via passing through the output path to the nllm command

I have the prompt template for the actual request to the reviewers:
git_reviewer/review.template.yml

