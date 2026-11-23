### 1. src/doctor.ts:969: the probe swallows the spawn error

Severity: P2

Verdict: CONFIRMED

Scenario: a missing binary reports "healthy".

```ts
  } catch {
    return { ok: true };
  }
```

END OF ROUND
