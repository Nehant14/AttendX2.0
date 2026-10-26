/** Today's date as YYYY-MM-DD in the user's LOCAL time zone (toISOString() uses UTC and is
 *  off by a day for part of every day in zones such as IST). */
export function localToday(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
