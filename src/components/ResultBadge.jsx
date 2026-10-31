import { resultLabel, resultTone } from "../utils.js";

export default function ResultBadge({ result, blasts }) {
  return <span className={`badge ${resultTone(result)}`}>{resultLabel(result, blasts)}</span>;
}
