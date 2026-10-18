// Serves a tests/fixtures recording as if the component had kept running: on the
// Nth request for a file, every counter, histogram, and summary count/sum value
// is the recorded value times N. Gauges and summary quantiles are served as
// recorded. A frozen recording otherwise gives the check a zero delta between
// scrapes, so its counters always report 0.
const fs = require('fs');

const ROOT = '/usr/share/nginx/fixtures';
const SCALED_TYPES = ['counter', 'histogram', 'summary'];
const SUFFIXES = ['_bucket', '_count', '_sum', '_total'];

function familyType(types, name) {
    if (types[name]) {
        return types[name];
    }
    const suffix = SUFFIXES.find((s) => name.endsWith(s) && types[name.slice(0, -s.length)]);
    return suffix ? types[name.slice(0, -suffix.length)] : undefined;
}

function scale(text, n) {
    const types = {};
    return text.split('\n').map((line) => {
        if (line.startsWith('# TYPE ')) {
            const parts = line.split(/\s+/);
            types[parts[2]] = parts[3];
            return line;
        }
        if (line === '' || line.startsWith('#')) {
            return line;
        }
        const labelsEnd = line.lastIndexOf('}');
        const nameEnd = line.search(/[{\s]/);
        const name = line.slice(0, nameEnd);
        const type = familyType(types, name);
        if (SCALED_TYPES.indexOf(type) < 0 || line.indexOf('quantile="') >= 0) {
            return line;
        }
        const head = labelsEnd >= 0 ? line.slice(0, labelsEnd + 1) : name;
        const rest = line.slice(head.length).trim().split(/\s+/);
        const value = Number(rest[0]);
        if (!isFinite(value)) {
            return line;
        }
        // Timestamps, if any, are dropped so the check uses scrape time.
        return head + ' ' + value * n;
    }).join('\n');
}

function serve(r) {
    const relative = r.uri.slice('/replay/'.length);
    if (relative.indexOf('..') >= 0) {
        r.return(400);
        return;
    }
    let text;
    try {
        text = fs.readFileSync(ROOT + '/' + relative, 'utf8');
    } catch (e) {
        r.return(404);
        return;
    }
    const n = ngx.shared.replay.incr(r.uri, 1, 0);
    r.headersOut['Content-Type'] = 'text/plain; version=0.0.4';
    r.return(200, scale(text, n));
}

export default { serve };
