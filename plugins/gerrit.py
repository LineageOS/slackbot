from __future__ import absolute_import
from __future__ import print_function

import re
from pygerrit2.rest import GerritRestAPI
import datetime

from rtmbot.core import Plugin

class GerritChangeFetcher(Plugin):
    def PostChangesInfo(self, data, rest, gerrit_url, changenum):
        # Use DETAILED_ACCOUNTS so we don't have to make a second API call for owner email and name
        change = rest.get("/changes/{}?o=DETAILED_ACCOUNTS".format(changenum))
        self.slack_client.api_call('chat.postMessage', channel=data['channel'], as_user=True, attachments=[
            {
                "fallback": "{}/#/c/{}: {}".format(gerrit_url,change['_number'],change['subject']),
                "color": "good",
                "title": "{}: {} ({})".format(change['_number'], change['subject'], 'Open' if change['status'] == 'NEW' else change['status'].capitalize()),
                "title_link": "{}/#/c/{}".format(gerrit_url,change['_number']),
                "mrkdwn_in": ["text"],
                'text': "*Project*: <https://review.lineageos.org/#/q/project:{project}|{project}> ({branch})\n*Topic*: {topic}\n*Owner*: <https://review.lineageos.org/#/q/owner:{username}|{name} ({email})>"
                    .format(
                        project = change['project'],
                        branch = change['branch'],
                        topic = '<{}/#/q/{topic}|{topic}>'.format(gerrit_url, topic = change['topic']) if 'topic' in change else 'None',
                        username = change['owner']['username'],
                        name = change['owner']['name'],
                        email = change['owner']['email']
                    )
            }
        ])
    def PostTopicInfo(self, data, rest, gerrit_url, topic_name):
        topic = rest.get("/changes/?q=topic:{}".format(topic_name))
        t_changes = ocn = mcn = acn = omcn = 0
        # Initialise these separately (unlike before), so we don't end up with
        # projects == branches
        projects,branches = [],[]
        for change in topic:
            if change['project'] not in projects:
                projects.append(change['project'])
            if change['branch'] not in branches:
                branches.append(change['branch'])
            if change['status'] == 'NEW':
                ocn = ocn + 1
                if change['mergeable']:
                    omcn = omcn + 1
            if change['status'] == 'MERGED':
                mcn = mcn + 1
            if change['status'] == 'ABANDONED':
                acn = acn + 1
            t_changes = t_changes + 1
        self.slack_client.api_call('chat.postMessage', channel=data['channel'], as_user=True, attachments=[
            {
                "fallback": "Topic: {}".format(topic_name),
                "color": "good",
                "title": "Topic: {}".format(topic_name),
                "title_link": "{}/#/q/topic:{}".format(gerrit_url,topic_name),
                "mrkdwn_in": ["text"],
                "text": "{total} commits across {projects} projects on {branches} branch(es)\n*Open*: <{base}/#/q/status:open%20AND%20topic:{name}|{ocn}>, of which <{base}/#/q/status:open%20AND%20is:mergeable%20AND%20topic:{name}|{omcn}> are mergeable\n*Merged*: <{base}/#/q/status:merged%20AND%20topic:{name}|{mcn}>\n*Abandoned*: <{base}/#/q/status:abandoned%20AND%20topic:{name}|{acn}>"
                    .format(
                        projects = len(projects),
                        branches = len(branches),
                        total = t_changes,
                        base = gerrit_url,
                        name = topic_name,
                        ocn = ocn,
                        omcn = omcn,
                        mcn = mcn,
                        acn = acn
                    )
            }
        ])
        return
    def process_message(self, data):
        text = data['text']
        changes = topics = []
        gerrit_url = "https://review.lineageos.org"
        rest = GerritRestAPI(url=gerrit_url)
        number_detections = 0
        for word in text.split():
            if gerrit_url in word:
                number_detections += 1
                if number_detections >= 4:
                    break # only print first 4 changes. any more is excessive
                topic = re.search(r'(?:topic:)(.+?(?:(?=[%\s+]|$|>)))',word)
                # explicitly check for url as prefix to avoid detecting numbers in project name queries
                # TODO: Find way to use $gerrit_url here
                change = re.search(r'(?:https:\/\/review\.lineageos\.org\/)(?:(?:#\/c\/)|)([0-9]{4,7})',word)
                if change is not None:
                    GerritChangeFetcher.PostChangesInfo(self, data, rest, gerrit_url, change.group(1))
                elif topic is not None:
                    GerritChangeFetcher.PostTopicInfo(self, data, rest, gerrit_url, topic.group(1))
                else:
                    return False
