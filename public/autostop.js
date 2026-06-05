/**
 * Silence-based auto-stop for Chainlit audio recording.
 *
 * Patches getUserMedia so we capture the same stream Chainlit uses,
 * then monitors RMS levels and clicks the stop button after sustained silence.
 */
(function () {
  var SILENCE_RMS    = 0.008;  // ~-42 dB — adjust up if noisy env, down if too sensitive
  var SILENCE_MS     = 1500;   // ms of silence after speech that triggers stop
  var MIN_SPEECH_MS  = 300;    // ignore silence until this much speech has been seen
  var monitorCtx     = null;

  var origGUM = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);

  navigator.mediaDevices.getUserMedia = async function (constraints) {
    var stream = await origGUM(constraints);
    if (constraints && constraints.audio) {
      monitorSilence(stream);
    }
    return stream;
  };

  function monitorSilence(stream) {
    if (monitorCtx) {
      try { monitorCtx.close(); } catch (e) {}
    }

    monitorCtx = new AudioContext();
    var src      = monitorCtx.createMediaStreamSource(stream);
    var analyser = monitorCtx.createAnalyser();
    analyser.fftSize = 1024;
    src.connect(analyser);

    var buf          = new Float32Array(analyser.fftSize);
    var lastSoundAt  = Date.now();
    var speechMs     = 0;
    var prevTickAt   = Date.now();

    function tick() {
      if (!stream.active) {
        try { monitorCtx.close(); } catch (e) {}
        return;
      }

      var now  = Date.now();
      var dt   = now - prevTickAt;
      prevTickAt = now;

      analyser.getFloatTimeDomainData(buf);
      var sum = 0;
      for (var i = 0; i < buf.length; i++) { sum += buf[i] * buf[i]; }
      var rms = Math.sqrt(sum / buf.length);

      if (rms > SILENCE_RMS) {
        lastSoundAt = now;
        speechMs   += dt;
      }

      if (speechMs >= MIN_SPEECH_MS && (now - lastSoundAt) >= SILENCE_MS) {
        clickStop();
        try { monitorCtx.close(); } catch (e) {}
        return;
      }

      requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }

  function clickStop() {
    // 1. aria-label / title containing "stop" or "record"
    var candidates = Array.from(document.querySelectorAll('button'));
    for (var i = 0; i < candidates.length; i++) {
      var btn   = candidates[i];
      var label = (btn.getAttribute('aria-label') || btn.getAttribute('title') || btn.textContent || '').toLowerCase();
      if (/stop/.test(label)) {
        btn.click();
        return;
      }
    }
    // 2. Fallback: any button whose svg path looks like a stop square (heuristic)
    for (var j = 0; j < candidates.length; j++) {
      var svg = candidates[j].querySelector('svg');
      if (svg && candidates[j].closest('[class*="audio"],[class*="record"],[class*="micro"]')) {
        candidates[j].click();
        return;
      }
    }
  }
})();
