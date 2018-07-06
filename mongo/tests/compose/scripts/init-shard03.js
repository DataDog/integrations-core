rs.initiate(
   {
      _id: "shard03",
      version: 1,
      members: [
         { _id: 0, host : "shard03a:27020" },
         { _id: 1, host : "shard03b:27020" },
      ]
   }
)
