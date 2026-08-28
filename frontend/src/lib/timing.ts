export function withMinDuration<T>(promise: Promise<T>, ms: number): Promise<T> {
  const wait = new Promise((resolve) => setTimeout(resolve, ms));
  return Promise.all([promise, wait]).then(([result]) => result);
}
