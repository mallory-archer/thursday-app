const lede = document.querySelector("#lede");
const main = document.querySelector("#main");
const distributionLead = document.querySelector("#distribution-lead");
const metrics = document.querySelector("#metrics");
const gaps = document.querySelector("#gaps");
const mixCaption = document.querySelector("#mix-caption");
const mixHead = document.querySelector("#mix-head");
const mixBody = document.querySelector("#mix-body");
const mixFoot = document.querySelector("#mix-foot");
const groupList = document.querySelector("#groups");
const colophon = document.querySelector("#colophon");

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value == null || value === "") continue;
    if (key === "className") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.append(child);
  return node;
}

function plural(count, singular) {
  return `${count} ${singular}${count === 1 ? "" : "s"}`;
}

function joinAnd(items) {
  if (items.length <= 1) return items[0] || "";
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}

function clusterLabel(cluster) {
  return `Cluster ${cluster}`;
}

function countsByCluster(group) {
  const counts = new Map();
  for (const entry of group.cluster_counts) counts.set(entry.cluster, entry.count);
  return counts;
}

function sizeBuckets(groups) {
  const tally = new Map();
  for (const group of groups) {
    const size = group.members.length;
    tally.set(size, (tally.get(size) || 0) + 1);
  }
  return [...tally.keys()]
    .sort((a, b) => b - a)
    .map((size) => ({ size, groups: tally.get(size) }));
}

function sizeSentence(groups) {
  const buckets = sizeBuckets(groups);
  if (buckets.length === 0) return "No groups.";
  const clause = (bucket) => {
    const verb = bucket.groups === 1 ? "has" : "have";
    return `${plural(bucket.groups, "group")} ${verb} ${plural(bucket.size, "student")}`;
  };
  if (buckets.length === 1) return `All ${clause(buckets[0])}.`;
  return `${joinAnd(buckets.map(clause))}.`;
}

function missingSentence(missingLists) {
  const count = missingLists.length;
  if (count === 0) return "Every group includes every cluster.";
  const verb = count === 1 ? "is" : "are";
  let sentence = `${plural(count, "group")} ${verb} missing a cluster`;
  if (missingLists.every((ids) => ids.length === 1)) {
    sentence += count === 1
      ? ", and that group is missing only one"
      : ", and each of those is missing only one";
  }
  return `${sentence}.`;
}

function appendSizeValue(dd, buckets) {
  buckets.forEach((bucket, index) => {
    if (index > 0) {
      const last = index === buckets.length - 1;
      dd.append(document.createTextNode(last && buckets.length === 2 ? " " : ", "));
      if (last) {
        dd.append(el("span", { className: "unit", text: "and" }));
        dd.append(document.createTextNode(" "));
      }
    }
    dd.append(document.createTextNode(String(bucket.size)));
  });
}

function presentClusterIds(clusters) {
  return clusters.filter((cluster) => cluster.students > 0).map((cluster) => cluster.cluster);
}

function missingClusterIds(group, presentIds) {
  const counts = countsByCluster(group);
  return presentIds.filter((id) => (counts.get(id) || 0) === 0);
}

function renderMetrics(data, groups, studentCount, missingLists) {
  const buckets = sizeBuckets(groups);
  const sizeValue = el("dd");
  appendSizeValue(sizeValue, buckets);
  const missingCount = data.groups_missing_a_cluster;
  const missingValue = el("dd");
  missingValue.append(
    document.createTextNode(String(missingCount)),
    document.createTextNode(" "),
    el("span", { className: "unit", text: missingCount === 1 ? "group" : "groups" }),
  );
  const missingNames = missingLists.map((ids) => ids.group);
  const missingFine = missingNames.length === 0
    ? "Every group includes every cluster"
    : `${missingNames.length === 1 ? "Group" : "Groups"} ${joinAnd(missingNames.map(String))}`;

  metrics.replaceChildren(
    el("div", {}, [
      el("dt", { text: "Groups" }),
      el("dd", { text: String(data.n_groups) }),
    ]),
    el("div", {}, [
      el("dt", { text: "Students" }),
      el("dd", { text: String(studentCount) }),
    ]),
    el("div", {}, [
      el("dt", { text: "Group sizes" }),
      sizeValue,
      el("dd", {
        className: "fine",
        text: buckets.map((bucket) => `${plural(bucket.groups, "group")} of ${bucket.size}`).join(" · "),
      }),
    ]),
    el("div", { className: missingCount > 0 ? "attention" : "" }, [
      el("dt", { text: "Missing a cluster" }),
      missingValue,
      el("dd", { className: "fine", text: missingFine }),
    ]),
  );
}

function renderGaps(clusters, groups) {
  const items = clusters.map((cluster) => {
    const absent = groups.filter((group) => {
      return (countsByCluster(group).get(cluster.cluster) || 0) === 0;
    }).length;
    let detail = `In all ${plural(groups.length, "group")}`;
    let short = false;
    if (cluster.students === 0) {
      detail = "No students in this cluster";
    } else if (absent > 0) {
      detail = `Missing from ${plural(absent, "group")}`;
      short = true;
    }
    return el("li", { className: short ? "short" : "" }, [
      el("span", { className: "kind-name" }, [
        el("span", { className: `dot c${cluster.cluster}`, "aria-hidden": "true" }),
        document.createTextNode(clusterLabel(cluster.cluster)),
      ]),
      el("span", { className: "detail", text: detail }),
    ]);
  });
  gaps.replaceChildren(...items);
}

function renderTable(data, clusters, groups, studentCount, presentIds) {
  const head = el("tr");
  head.append(
    el("th", { scope: "col", text: "Group" }),
    el("th", { scope: "col", text: "Students" }),
  );
  for (const cluster of clusters) {
    head.append(el("th", { scope: "col", text: clusterLabel(cluster.cluster) }));
  }
  head.append(el("th", { scope: "col", text: "Missing" }));

  const rows = groups.map((group) => {
    const counts = countsByCluster(group);
    const missing = missingClusterIds(group, presentIds);
    const row = el("tr", { className: missing.length > 0 ? "short" : "" });
    const label = el("th", { scope: "row" });
    label.append(el("a", { href: `#group-${group.group}`, text: String(group.group) }));
    row.append(label, el("td", { text: String(group.members.length) }));
    for (const cluster of clusters) {
      const count = counts.get(cluster.cluster) || 0;
      row.append(el("td", {
        className: count === 0 ? "zero" : "",
        text: String(count),
      }));
    }
    row.append(el("td", {
      className: "missing",
      text: missing.length > 0 ? joinAnd(missing.map(clusterLabel)) : "None",
    }));
    return row;
  });

  const foot = el("tr");
  foot.append(
    el("th", { scope: "row", text: "All groups" }),
    el("td", { text: String(studentCount) }),
  );
  for (const cluster of clusters) foot.append(el("td", { text: String(cluster.students) }));
  foot.append(el("td", { text: plural(data.groups_missing_a_cluster, "group") }));

  const summary = clusters
    .map((cluster) => `${clusterLabel(cluster.cluster)}: ${cluster.students}`)
    .join(", ");
  mixCaption.textContent = `Cluster counts across the ${plural(groups.length, "group")}. ${summary}.`;
  mixHead.replaceChildren(head);
  mixBody.replaceChildren(...rows);
  mixFoot.replaceChildren(foot);
}

function renderCards(clusters, groups, presentIds) {
  const cards = groups.map((group) => {
    const counts = countsByCluster(group);
    const missing = missingClusterIds(group, presentIds);
    const complete = missing.length === 0;
    const mix = el("ul", {
      className: "mix",
      "aria-label": `Cluster mix for group ${group.group}`,
    });
    for (const cluster of clusters) {
      const count = counts.get(cluster.cluster) || 0;
      mix.append(el("li", { className: count === 0 ? "is-zero" : "" }, [
        el("span", { className: `dot c${cluster.cluster}`, "aria-hidden": "true" }),
        document.createTextNode(clusterLabel(cluster.cluster)),
        el("span", { className: "count", text: String(count) }),
      ]));
    }
    const roster = el("ul", { className: "roster" });
    for (const name of group.members) {
      roster.append(el("li", {}, [el("span", { className: "name", text: name })]));
    }
    const article = el("article", {
      className: complete ? "card complete" : "card short",
      id: `group-${group.group}`,
    }, [
      el("div", { className: "card-top" }, [
        el("h3", { text: `Group ${group.group}` }),
        el("p", { className: "size", text: plural(group.members.length, "student") }),
      ]),
      el("p", {
        className: complete ? "status complete" : "status short",
        text: complete ? "All clusters present" : `Missing ${joinAnd(missing.map(clusterLabel))}`,
      }),
      mix,
      roster,
    ]);
    return el("li", {}, [article]);
  });
  groupList.replaceChildren(...cards);
}

function render(data) {
  const clusters = [...data.clusters].sort((a, b) => a.cluster - b.cluster);
  const groups = [...data.groups].sort((a, b) => a.group - b.group);
  const presentIds = presentClusterIds(clusters);
  const studentCount = groups.reduce((sum, group) => sum + group.members.length, 0);
  const missingLists = groups
    .map((group) => ({ group: group.group, ids: missingClusterIds(group, presentIds) }))
    .filter((entry) => entry.ids.length > 0);

  if (clusters.length > 0) {
    document.documentElement.style.setProperty("--cluster-cols", String(clusters.length));
  }

  lede.textContent = `${plural(studentCount, "student")} placed in ${plural(data.n_groups, "group")} across ${plural(clusters.length, "cluster")}. A group is complete when every cluster in the class is present.`;
  distributionLead.textContent = groups.length === 0
    ? "No groups."
    : `${sizeSentence(groups)} ${missingSentence(missingLists.map((entry) => entry.ids))}`;

  renderMetrics(data, groups, studentCount, missingLists);
  renderGaps(clusters, groups);
  renderTable(data, clusters, groups, studentCount, presentIds);
  renderCards(clusters, groups, presentIds);
  colophon.textContent = `${plural(data.n_groups, "group")}, ${plural(studentCount, "student")}, ${plural(clusters.length, "cluster")}.`;
  main.hidden = false;
}

async function loadGroups() {
  const response = await fetch("/api/groups");
  if (!response.ok) throw new Error("Request failed");
  const data = await response.json();
  if (!Array.isArray(data.groups) || !Array.isArray(data.clusters)) {
    throw new Error("Unexpected response");
  }
  render(data);
}

loadGroups().catch(() => {
  lede.textContent = "Could not load groups.";
});
