"""Mock LinkedIn Easy Apply harness for the Easy Apply saga (Phase 3, T3.6).

A tiny Flask app simulating the LinkedIn Easy Apply modal flow:
- /job/<id> renders a job page with an Easy Apply button
- clicking Easy Apply reveals a 3-step modal (form -> review -> submit)
- submitting reveals a success marker

Used by the opt-in live browser test (JOBOT_RUN_LIVE_BROWSER=1) and available
as a deterministic target for the saga state machine.
"""

from flask import Flask, render_template_string

app = Flask(__name__)

HARNESS_HTML = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Mock LinkedIn</title></head>
<body>
<button class="jobs-apply-button" onclick="show('step1')">Easy Apply</button>
<div id="step1" class="step" style="display:none">
  <form>
    <input type="text" name="email" placeholder="Email">
    <textarea placeholder="Cover note"></textarea>
    <button aria-label="Next" onclick="show('step2')">Next</button>
  </form>
</div>
<div id="step2" class="step" style="display:none">
  <form>
    <input type="text" name="phone" placeholder="Phone">
    <button aria-label="Review" onclick="show('step3')">Review</button>
  </form>
</div>
<div id="step3" class="step" style="display:none">
  <form>
    <button aria-label="Submit application" onclick="show('success')">Submit application</button>
  </form>
</div>
<div id="success" class="step post-apply" style="display:none">
  <h3>Application submitted</h3>
</div>
<script>
function show(id) {
  document.querySelectorAll('.step').forEach(function (s) { s.style.display = 'none'; });
  document.getElementById(id).style.display = 'block';
}
</script>
</body>
</html>"""

NO_BUTTON_HTML = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Mock LinkedIn - No Easy Apply</title></head>
<body>
<h1>This job requires external application</h1>
<a href="https://example.com">Apply on company site</a>
</body>
</html>"""


@app.route("/job/<job_id>")
def job(job_id: str):
    if job_id == "no_easy_apply":
        return render_template_string(NO_BUTTON_HTML)
    return render_template_string(HARNESS_HTML)
