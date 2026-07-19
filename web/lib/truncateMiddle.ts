/** Middle-ellipsis for hashes / addresses shown in dense UI. */

export const HASH_DISPLAY_HEAD = 4;
export const HASH_DISPLAY_TAIL = 4;

export function truncateMiddle(
  value: string,
  head: number = HASH_DISPLAY_HEAD,
  tail: number = HASH_DISPLAY_TAIL,
): string {
  if (value.length <= head + tail + 1) {
    return value;
  }
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}
