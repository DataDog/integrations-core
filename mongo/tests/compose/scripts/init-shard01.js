rs.initiate(
   {
      _id: "shard01",
      version: 1,
      members: [
         { _id: 0, host : "shard01a:27018", priority: 1},
         { _id: 1, host : "shard01b:27019", priority: 0.5 },
         { _id: 2, host : "shard01c:27020", arbiterOnly: true},
      ]
   }
)
