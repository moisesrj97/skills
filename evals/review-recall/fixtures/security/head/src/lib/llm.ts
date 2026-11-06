export const llm = {
  async complete(prompt: string): Promise<string> {
    const res = await fetch(process.env.LLM_URL!, { method: 'POST', body: JSON.stringify({ prompt }) });
    return (await res.json()).text;
  },
};
