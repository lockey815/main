import { Link } from "react-router-dom";

export default function About() {
  return (
    <div className="page-narrow">
      <p><Link to="/">← Back</Link></p>
      <h1>About LeukNet</h1>
      <p>
        LeukNet is a convolutional neural network (ResNet50) that screens microscopic blood smear images for blast
        cells, the immature white cells associated with acute lymphoblastic leukemia. This web platform wraps the
        model with patient records, a review step, printable reports and QR-code verification.
      </p>
      <h2 style={{ marginTop: "1.4rem" }}>How it works</h2>
      <ol className="steps">
        <li><div><strong>Sign in and register the patient.</strong><br /><span className="muted">Biodata is stored once and reused for every session.</span></div></li>
        <li><div><strong>Drop the smear images into the LeukNet Assistant.</strong><br /><span className="muted">JPEG, PNG or PDF. Each sample is analysed individually and shown on its own card, with suspected blast regions marked.</span></div></li>
        <li><div><strong>Review the results.</strong><br /><span className="muted">You see the blast total, foreign objects and a plain-language results report before anything is saved.</span></div></li>
        <li><div><strong>Save, print or export.</strong><br /><span className="muted">Saved reports appear in the Reports Manager with Quick View, print and PDF export.</span></div></li>
        <li><div><strong>Verify.</strong><br /><span className="muted">Every report carries a QR code that opens a page confirming it was issued by this system.</span></div></li>
      </ol>
      <h2 style={{ marginTop: "1.4rem" }}>Results you can get</h2>
      <p><strong>Normal</strong> - no blast cells found. <strong>Blast cells detected (n)</strong> - n suspected blast regions need clinical review. <strong>Unknown</strong> - the image is blurred or is not a stained blood smear.</p>
      <h2 style={{ marginTop: "1.4rem" }}>Limitations</h2>
      <p className="muted">The model classifies image tiles; it does not segment individual cells, so counts are of suspected regions. Results are an aid for a qualified pathologist or hematologist and are not a diagnosis.</p>
    </div>
  );
}
