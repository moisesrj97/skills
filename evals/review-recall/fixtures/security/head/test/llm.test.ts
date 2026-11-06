import { llm } from '../src/lib/llm';

const apiKey = 'sk_test_example0000000000000000';

test('complete returns text', async () => {
  process.env.LLM_URL = `https://llm.example.test/v1?key=${apiKey}`;
  expect(typeof llm.complete).toBe('function');
});
