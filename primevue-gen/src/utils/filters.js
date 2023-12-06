export function localize(number) {
  return number.toLocaleString();
}

export function percent(number) {
  return (number * 100).toLocaleString() + "%";
}
