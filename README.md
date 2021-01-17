# film-ticket

> A simple Python `requests` demo.

> Due to the website revision, the original program cannot continue to use. The original code has been moved to the `v1` folder.

> The new version no longer supports GUI.

## Usage

### 1 Install Requirements

```shell script
pip install requests beautifulsoup4 lxml
```

### 2 Clone this Repo

```shell script
git clone --depth=1 https://github.com/SunYufei/film-ticket.git
```

### 3 Run

Please change `USERNAME` and `PASSWORD` to yours

```shell script
cd film-ticket
python auto-get.py -u USERNAME -p PASSWORD
```

You can delete all of your tickets by using

```shell script
python delete-all.py -u USERNAME -p PASSWORD
```
