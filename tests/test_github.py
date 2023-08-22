from sqlcritic.github import Pull, Repo

# need to temporarily paste a real token here if you want to update the cassettes
token = "test"


def test_pull(vcr_cassette):
    repo = Repo("scttnlsn/sql-critic-demo", token)
    pull = repo.pull(2)

    assert pull.base_sha == "1ad47278d53ef55208fce0396235e3d31220c0f1"
    assert pull.head_sha == "940ed012edc166397c86e27c4cd64b5960f1a931"


def test_pull_comment(vcr_cassette):
    repo = Repo("scttnlsn/sql-critic-demo", token)
    pull = repo.pull(2)

    pull.comment(["foo"])
    pull.comment(["bar"])

    comment = pull.bot_comment()

    # assert it updates the same comment
    assert "bar" in comment.body
    assert "foo" not in comment.body


def test_commit_pulls(vcr_cassette):
    repo = Repo("scttnlsn/sql-critic-demo", token)
    pulls = repo.pulls("9c4868ed45c1e680ed7b2456456340d21a63f6e3")
    assert len(pulls) == 1
    assert pulls[0].number == 5
